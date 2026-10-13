"""Offline full-sample auditing; never writes dispositions to the CRM."""

from collections import Counter
from typing import Any

from src.audit_policy.answer_tree import answer_prompting_paths
from src.audit_policy.models import AuditProjectPolicy
from src.domain.models import SurveyQuestion
from src.full_sample.audit_adapter import run_full_question_audit
from src.full_sample.survey_options import canonical_options_from_question


def index_by_tag(rows):
    result = {}
    for row in rows:
        tag = row["tag"]
        if tag in result:
            raise ValueError(f"Duplicate tag: {tag}")
        result[tag] = row
    return result


def compare_disposition(suggestion, human_side):
    """Compare ordered labels, not CRM selectedOptions indices as IDs."""
    selected = (human_side or {}).get("selectedOptions")
    if not isinstance(selected, dict) or not selected:
        return {"status": "UNLABELED"}
    if not all(str(key).isdigit() for key in selected):
        return {"status": "UNSUPPORTED_LABEL"}
    expected = [selected[key] for key in sorted(selected, key=lambda k: int(k))]
    if not all(isinstance(value, str) for value in expected):
        return {"status": "UNSUPPORTED_LABEL"}
    actual = None
    if suggestion:
        actual = suggestion.disposition_path or (
            [suggestion.disposition_text] if suggestion.disposition_text else None
        )
    return {
        "status": "NO_SUGGESTION" if not actual else (
            "MATCH" if actual == expected else "MISMATCH"
        ),
        "human_path": expected,
        "suggested_path": actual,
    }


def evaluate_full_sample(
    *, dialogues: list[dict[str, Any]], windows: list[dict[str, Any]],
    survey_definition: dict[str, Any], policy: AuditProjectPolicy,
    human_audit: dict[str, Any], tags: list[str] | None = None,
    prompting_aware_answers: bool = False,
) -> dict[str, Any]:
    # prompting_aware_answers enables "Yes - No Prompting Done" on flat
    # prompting trees. Off by default: the prompting detector reports
    # no prompting whenever follow-up speech is absent, including when
    # it was lost upstream, and missed human-labelled prompting.
    dialogue_map = index_by_tag(dialogues)
    window_map = index_by_tag(windows)
    survey_map = index_by_tag(survey_definition["questions"])
    requested = list(dict.fromkeys(tags if tags is not None else window_map))
    rows = []
    for tag in requested:
        missing = [name for name, mapping in (
            ("dialogue", dialogue_map), ("question_window", window_map),
            ("survey_definition", survey_map), ("policy", policy.tags),
        ) if tag not in mapping]
        if missing:
            rows.append({"tag": tag, "status": "MISSING_INPUT",
                         "missing": missing, "review_required": True})
            continue
        tag_policy = policy.tags[tag]
        if not tag_policy.active:
            rows.append({"tag": tag, "status": "INACTIVE_POLICY",
                         "review_required": True})
            continue
        if tag_policy.project_code != policy.project_code or tag_policy.tag != tag:
            raise ValueError(f"Policy scope mismatch: {tag}")
        definition = survey_map[tag]
        window = window_map[tag]
        # The survey definition supplies the authoritative question wording.
        dialogue = {**dialogue_map[tag], "question_text": definition["question_text"]}
        no_prompting_path, prompting_path = (
            answer_prompting_paths(tag_policy.answer_validation.dispositions)
            if prompting_aware_answers else (None, None))
        result = run_full_question_audit(
            question=SurveyQuestion(
                key=tag, text_hi=definition["question_text"],
                type=definition["question_type"],
                selected_answer=window.get("stored_response"),
            ),
            rich_dialogue=dialogue, question_window=window,
            canonical_options=canonical_options_from_question(definition),
            tag_policy=tag_policy,
            no_prompting_path=no_prompting_path, prompting_path=prompting_path,
            # Only sides the policy audits need a suggestion.
            require_question_disposition=tag_policy.question_validation.enabled,
            require_answer_disposition=tag_policy.answer_validation.enabled,
        )
        human = human_audit.get(tag) or {}
        rows.append({
            "tag": tag, "status": "EVALUATED",
            **result.model_dump(mode="json"),
            "comparison": {
                "question": compare_disposition(result.audit.question_disposition, human.get("quesVal")),
                "answer": compare_disposition(result.audit.answer_disposition, human.get("ansVal")),
            },
        })
    evaluated = [row for row in rows if row["status"] == "EVALUATED"]
    return {
        "schema_version": 1,
        "project_code": policy.project_code,
        "summary": {
            "requested": len(rows), "evaluated": len(evaluated),
            "not_evaluated": len(rows) - len(evaluated),
            "actions": dict(Counter(row["automation"]["action"] for row in evaluated)),
            "comparisons": {
                side: dict(Counter(row["comparison"][side]["status"] for row in evaluated))
                for side in ("question", "answer")
            },
        },
        "questions": rows,
    }
