import json

import pytest

from src.audit_policy.models import AuditProjectPolicy, DispositionNode
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


def flat_prompting_inputs():
    data = inputs()
    data["policy"].tags["state_govt_change"].answer_validation.dispositions = [
        DispositionNode(id=3001, text="Yes - No Prompting Done"),
        DispositionNode(id=3002, text="Mismatch", comments_required=True),
        DispositionNode(id=3003, text="Prompting -Party A"),
    ]
    data["human_audit"] = {}
    return data


def test_flat_prompting_mapping_is_off_by_default():
    row = evaluate_full_sample(**flat_prompting_inputs())["questions"][0]
    assert row["audit"]["prompting_status"] is None
    assert row["audit"]["answer_disposition"]["disposition_id"] is None


def test_opt_in_flat_prompting_mapping_is_prefill_only():
    row = evaluate_full_sample(
        **flat_prompting_inputs(), prompting_aware_answers=True,
    )["questions"][0]
    assert row["audit"]["prompting_status"] == "NO_PROMPTING_EVIDENCE"
    assert row["audit"]["answer_disposition"]["disposition_text"] == "Yes - No Prompting Done"
    answer = [p for p in row["automation"]["proposals"] if p["side"] == "answer"][0]
    assert answer["action"] == "PREFILL"
    assert row["automation"]["action"] != "AUTO_FILL"


def test_dropped_overlap_turn_blocks_no_prompting_suggestion():
    data = flat_prompting_inputs()
    data["dialogues"][0]["turns"].insert(1, make_turn(
        3, "respondent", 12.1, 12.4, "कुछ", raw_overlap=True, raw_overlap_sec=0.3,
    ))
    row = evaluate_full_sample(**data, prompting_aware_answers=True)["questions"][0]

    assert row["audit"]["prompting_status"] == "UNCERTAIN"
    assert row["audit"]["answer_disposition"]["disposition_id"] is None


def test_overlapping_window_withholds_answer_but_keeps_question():
    data = inputs()
    data["windows"][0]["overlap_review_required"] = True
    row = evaluate_full_sample(**data)["questions"][0]

    sides = {p["side"]: p["action"] for p in row["automation"]["proposals"]}
    assert sides == {"question": "PREFILL"}
    assert "answer" in row["automation"]["unresolved_sides"]
    assert row["automation"]["action"] == "PREFILL"
    assert any("overlaps another question" in r for r in row["automation"]["reasons"])


def test_window_without_overlap_flag_is_unchanged():
    row = evaluate_full_sample(**inputs())["questions"][0]
    assert {p["side"] for p in row["automation"]["proposals"]} == {"question", "answer"}


def test_inactive_policy_is_not_executed():
    data = inputs()
    data["policy"].tags["state_govt_change"].active = False
    report = evaluate_full_sample(**data)
    assert report["summary"]["evaluated"] == 0
    assert report["questions"][0]["status"] == "INACTIVE_POLICY"


def test_side_without_validation_is_not_required():
    data = inputs()
    data["policy"].tags["state_govt_change"].question_validation.enabled = False
    row = evaluate_full_sample(**data)["questions"][0]

    assert "question" not in row["automation"]["unresolved_sides"]
    assert [p["side"] for p in row["automation"]["proposals"]] == ["answer"]


def test_paraphrased_question_gets_asked_right():
    data = inputs()
    data["dialogues"][0]["turns"][0]["transcript"] = "अच्छा दीदी आप राज्य सरकार में बदलाव देखना चाहती हैं"
    row = evaluate_full_sample(**data)["questions"][0]

    assert row["audit"]["question_validation_status"] == "ASKED_RIGHT"
    question = [p for p in row["automation"]["proposals"] if p["side"] == "question"][0]
    assert question["disposition"]["disposition_text"] == "Asked Right"


def test_overlapping_question_is_prefill_only():
    data = inputs()
    data["dialogues"][0]["turns"][0]["raw_cross_speaker_overlap"] = True
    row = evaluate_full_sample(**data)["questions"][0]

    question = [p for p in row["automation"]["proposals"] if p["side"] == "question"][0]
    assert question["action"] == "PREFILL"
    assert row["audit"]["question_review_required"] is True


def test_script_matching_can_be_switched_off():
    data = inputs()
    data["dialogues"][0]["turns"][0]["transcript"] = "अच्छा दीदी आप राज्य सरकार में बदलाव देखना चाहती हैं"
    row = evaluate_full_sample(**data, script_matching=False)["questions"][0]

    from src.question_validation.fuzzy import validate_question_text
    legacy = validate_question_text(QUESTION_TEXT, data["dialogues"][0]["turns"][0]["transcript"])
    assert row["audit"]["question_validation_confidence"] == legacy.confidence


def test_matched_passage_anchors_when_no_single_turn_resembles_the_script():
    from src.full_sample.audit_adapter import build_safe_audit_inputs

    dialogue = make_dialogue([
        make_turn(1, "agent", 10.0, 12.0, "दीदी वो वाली बात बताइए"),
        make_turn(2, "respondent", 12.5, 13.5, "हाँ"),
    ])
    without = build_safe_audit_inputs(dialogue, make_window())
    with_fallback = build_safe_audit_inputs(dialogue, make_window(), fallback_anchor_turn_index=1)

    assert without.trace.anchor_found is False
    assert with_fallback.trace.anchor_found is True
    assert with_fallback.trace.anchor_method == "SCRIPT_MATCH_PASSAGE"
    assert [t.speaker for t in with_fallback.dialogue.turns] == ["agent", "respondent"]
