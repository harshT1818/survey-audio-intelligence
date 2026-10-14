"""Convert an audited interview into the data the demo page displays.

Works the same for the synthetic interview and for a real sample folder; a
real one is written under data/private/ and opened in the page locally.
"""

import math
import random
from typing import Any

from src.audit_policy.answer_tree import (
    FLAT_PROMPTING,
    INTRODUCTION,
    MATCH_MISMATCH,
    NESTED_PROMPTING,
    classify_answer_tree,
)
from src.audit_policy.models import AuditProjectPolicy, DispositionNode
from src.full_sample.audit_runner import piped_answer_labels
from src.full_sample.survey_options import canonical_options_from_question, primary_label
from src.question_validation.script_match import (
    STOPWORDS,
    WH,
    assess_asking,
    build_option_index,
    build_profiles,
    score_speech,
    tokens,
)

SCHEMA = "auditor-assist-demo/1"

# Why an answer side gets no suggestion when the cause is its tree, not the evidence.
TREE_NOTES = {
    NESTED_PROMPTING: "The rule for choosing between 'No prompting done' and 'Respondent says …' is waiting on the audit team, so the answer is left to the auditor.",
    INTRODUCTION: "Rules for judging the introduction are not built yet, so the answer is left to the auditor.",
    FLAT_PROMPTING: "Prompting rules for this answer are switched off until the audit team confirms them.",
}
PLAIN_REASONS = {"No dialogue turns were provided.": "No speech was found in this question's window."}


def _paths(nodes: list[DispositionNode], prefix=()) -> list[dict[str, Any]]:
    out = []
    for node in nodes:
        path = [*prefix, node.text]
        if node.children:
            out += _paths(node.children, path)
        else:
            out.append({"path": path, "comments_required": node.comments_required})
    return out


def _stored_text(stored: Any) -> str:
    values = stored if isinstance(stored, list) else [stored]
    return ", ".join(primary_label(str(v)) or str(v) for v in values if v not in (None, ""))


def _script_words(spoken_script: str, matched: set[str], heard_wh: bool) -> list[dict[str, str]]:
    raw = spoken_script.replace("|", " ").split()
    words, i = [], 0
    while i < len(raw):
        # A compound written as two words (विधान सभा) is one matching unit.
        pair = raw[i:i + 2]
        joined = len(pair) == 2 and all(tokens(w) for w in pair) and len(tokens(" ".join(pair))) == 1
        group = pair if joined else raw[i:i + 1]
        i += len(group)
        units = tokens(" ".join(group))
        if not units:
            continue
        unit = units[0]
        if unit == WH:
            state = "matched" if heard_wh else "missing"
        elif unit in STOPWORDS:
            state = "filler"
        else:
            state = "matched" if unit in matched else "missing"
        words += [{"text": word, "state": state} for word in group]
    return words


def _turn_flags(turn: dict[str, Any]) -> list[str]:
    flags = []
    if turn.get("undetected_by_diarization"):
        flags.append("unattributed")
    if turn.get("raw_cross_speaker_overlap"):
        flags.append("overlap")
    if "core" not in (turn.get("regions") or []):
        flags.append("context")
    return flags


def synthetic_waveform(turns: list[dict[str, Any]], duration: float, bins: int = 720, seed: int = 7) -> list[float]:
    """Speech-like loudness envelope for a fictional interview (no audio exists)."""
    rng = random.Random(seed)
    level = {"agent": 0.62, "respondent": 0.48, "unknown": 0.2}
    out = []
    for i in range(bins):
        t = (i + 0.5) * duration / bins
        value = 0.025 + rng.random() * 0.02
        for turn in turns:
            if turn["start_sec"] <= t <= turn["end_sec"]:
                syllable = 0.55 + 0.45 * abs(math.sin(t * 7.3 + turn["start_sec"])) * (0.6 + 0.4 * rng.random())
                value = level.get(turn["role"], 0.3) * syllable
        out.append(round(min(1.0, value), 3))
    return out


def build_view_model(
    *,
    report: dict[str, Any],
    dialogues: list[dict[str, Any]],
    windows: list[dict[str, Any]],
    survey_definition: dict[str, Any],
    policy: AuditProjectPolicy,
    interview_turns: list[dict[str, Any]],
    waveform: list[float],
    duration_sec: float,
    interview_id: str,
    synthetic: bool,
) -> dict[str, Any]:
    dialogue_map = {d["tag"]: d for d in dialogues}
    window_map = {w["tag"]: w for w in windows}
    definitions = {q["tag"]: q for q in survey_definition["questions"]}
    profiles = build_profiles(
        {tag: q.get("question_text") or "" for tag, q in definitions.items()},
        piped_answer_labels(windows),
    )

    questions = []
    for row in report["questions"]:
        if row.get("status") != "EVALUATED":
            continue
        tag = row["tag"]
        tag_policy = policy.tags[tag]
        window = window_map[tag]
        dialogue = dialogue_map[tag]
        definition = definitions[tag]
        assessment = assess_asking(
            profiles[tag], dialogue["turns"], float(window["start_sec"]), float(window["end_sec"]),
            build_option_index(canonical_options_from_question(definition)),
            bool(definition.get("do_not_read_options")),
        )
        matched = set()
        if assessment.text:
            score = score_speech(profiles[tag], assessment.text)
            matched = set(score.matched)
            heard_wh = score.has_wh
        else:
            heard_wh = False

        proposals = {p["side"]: p for p in row["automation"]["proposals"]}
        audit = row["audit"]
        evidence = audit.get("evidence") or {}
        passage = set(assessment.turn_indices)
        anchor_id = row["trace"].get("anchor_turn_id")
        tree = classify_answer_tree(tag_policy.answer_validation.dispositions)
        answer_notes = [PLAIN_REASONS.get(r, r) for r in (row["corroboration"].get("reasons") or []) if r]
        if "answer" not in proposals and tree != MATCH_MISMATCH:
            answer_notes = [TREE_NOTES.get(tree, "This answer tree is not recognised, so no answer is suggested."), *answer_notes]

        def side(name: str, enabled: bool, extra: dict[str, Any]) -> dict[str, Any]:
            proposal = proposals.get(name)
            disposition = proposal["disposition"] if proposal else None
            return {
                "enabled": enabled,
                "action": proposal["action"] if proposal else None,
                "suggestion": (disposition.get("disposition_path") or [disposition.get("disposition_text")]) if disposition else None,
                "reason": proposal["reason"] if proposal else None,
                "human": row["comparison"][name].get("human_path"),
                "agreement": row["comparison"][name]["status"],
                **extra,
            }

        questions.append({
            "tag": tag,
            "index": window.get("question_index"),
            "title": tag_policy.placeholder or tag,
            "window": [float(window["start_sec"]), float(window["end_sec"])],
            "action": row["automation"]["action"],
            "script": profiles[tag].spoken_script,
            "script_words": _script_words(profiles[tag].spoken_script, matched, heard_wh),
            "do_not_read_options": bool(definition.get("do_not_read_options")),
            "turns": [{
                "start": t.get("start_sec"), "end": t.get("end_sec"), "role": t.get("role", "unknown"),
                "speaker": t.get("speaker_id"), "text": t.get("transcript") or "",
                "status": t.get("asr_status"), "flags": _turn_flags(t),
                "in_passage": t.get("turn_index") in passage,
                "anchor": f"{tag}:turn:{t.get('turn_index')}" == anchor_id,
            } for t in dialogue["turns"]],
            "question": side("question", tag_policy.question_validation.enabled, {
                "coverage": assessment.coverage,
                "passage": assessment.text,
                "status": assessment.status,
                "named_options": [primary_label(v) or v for v in assessment.named_options],
                "notes": assessment.reasons,
            }),
            "answer": side("answer", tag_policy.answer_validation.enabled, {
                "recorded": _stored_text(window.get("stored_response")),
                "heard": evidence.get("respondent_text") or "",
                "tree": tree,
                "notes": answer_notes[:2],
            }),
            "options": {
                "question": _paths(tag_policy.question_validation.dispositions),
                "answer": _paths(tag_policy.answer_validation.dispositions),
            },
            "review_reasons": row["automation"].get("reasons") or [],
        })

    actions = [q["action"] for q in questions]
    agreement = {"agree": 0, "disagree": 0}
    for q in questions:
        for name in ("question", "answer"):
            status = q[name]["agreement"]
            if status == "MATCH":
                agreement["agree"] += 1
            elif status == "MISMATCH":
                agreement["disagree"] += 1

    return {
        "schema": SCHEMA,
        "synthetic": synthetic,
        "interview": {
            "id": interview_id,
            "project": policy.project_name or policy.project_code,
            "duration_sec": round(duration_sec, 2),
            "language": "Hindi",
        },
        "summary": {
            "questions": len(questions),
            "auto": actions.count("AUTO_FILL"),
            "prefill": actions.count("PREFILL"),
            "review": actions.count("HUMAN_REVIEW"),
            "agreement": agreement,
        },
        "timeline": {
            "turns": [{
                "start": t["start_sec"], "end": t["end_sec"], "role": t.get("role", "unknown"),
                "speaker": t.get("speaker_id"), "text": t.get("transcript") or "",
                "unattributed": bool(t.get("undetected_by_diarization")),
            } for t in interview_turns],
            "waveform": waveform,
        },
        "questions": questions,
    }
