import json

import pytest

from src.audit_policy.models import AuditProjectPolicy
from src.full_sample.audit_runner import compare_disposition, evaluate_full_sample
from test_audit_adapter import QUESTION_TEXT, make_dialogue, make_policy, make_turn, make_window


def inputs():
    policy = make_policy()
    return dict(
        dialogues=[make_dialogue([
            make_turn(1, "agent", 10.0, 12.0, QUESTION_TEXT),
            make_turn(2, "respondent", 12.5, 13.5, "हाँ"),
        ])],
        windows=[{**make_window(), "stored_response": "Yes"}],
        survey_definition={"questions": [{
            "tag": policy.tag, "question_text": QUESTION_TEXT,
            "question_type": "single_choice", "resolution_ready": True,
            "choice_catalog_status": "STATIC",
            "choices": [{"option_text": "Yes", "hindi": "हाँ"},
                        {"option_text": "No", "hindi": "नहीं"}],
        }]},
        policy=AuditProjectPolicy(project_code=policy.project_code, tags={policy.tag: policy}),
        human_audit={policy.tag: {
            "quesVal": {"selectedOptions": {"0": "Asked Right"}},
            "ansVal": {"selectedOptions": {"0": "Mismatch"}},
        }},
    )


def test_runner_serializes_adapter_and_compares_labels():
    report = evaluate_full_sample(**inputs())
    row = json.loads(json.dumps(report))["questions"][0]
    assert row["automation"]["action"] == "AUTO_FILL"
    assert row["comparison"]["question"]["status"] == "MATCH"
    assert row["comparison"]["answer"]["status"] == "MISMATCH"
    assert row["trace"]["anchor_found"] is True
    assert row["corroboration"]["resolved_option"] == "Yes"


def test_runner_preserves_overlap_and_review_decision():
    data = inputs()
    data["dialogues"][0]["turns"].insert(1, make_turn(
        3, "respondent", 12.1, 12.4, "कुछ", raw_overlap=True, raw_overlap_sec=0.3,
    ))
    row = evaluate_full_sample(**data)["questions"][0]
    assert row["automation"]["action"] == "PREFILL"
    assert row["trace"]["rejected_turns"][0]["material_for_review"] is True


def test_missing_inputs_remain_visible_and_unlabeled_is_not_match():
    data = inputs()
    data["human_audit"] = {}
    report = evaluate_full_sample(**data, tags=["state_govt_change", "missing"])
    assert report["summary"]["not_evaluated"] == 1
    assert report["questions"][1]["status"] == "MISSING_INPUT"
    assert report["questions"][0]["comparison"]["answer"]["status"] == "UNLABELED"
    assert compare_disposition(None, {"selectedOptions": {"0": "Asked Right"}})["status"] == "NO_SUGGESTION"


def test_duplicate_tags_and_wrong_project_are_rejected():
    data = inputs()
    data["windows"] *= 2
    with pytest.raises(ValueError, match="Duplicate tag"):
        evaluate_full_sample(**data)
    data = inputs()
    data["policy"].project_code = "wrong"
    with pytest.raises(ValueError, match="scope mismatch"):
        evaluate_full_sample(**data)


def test_inactive_policy_is_not_executed():
    data = inputs()
    data["policy"].tags["state_govt_change"].active = False
    report = evaluate_full_sample(**data)
    assert report["summary"]["evaluated"] == 0
    assert report["questions"][0]["status"] == "INACTIVE_POLICY"
