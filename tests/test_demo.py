import json
from pathlib import Path

from scripts.build_demo import build_synthetic
from src.demo.view_model import _script_words
from src.question_validation.script_match import tokens

EXPECTED_ACTIONS = {
    "mla_awareness": "AUTO_FILL",
    "age": "PREFILL",
    "state_govt_change": "PREFILL",
    "state_govt_change_party": "PREFILL",
    "mla_choice": "PREFILL",
    "vs_past_candidate": "HUMAN_REVIEW",
    "vs_past_party": "HUMAN_REVIEW",
    "cm_choice": "HUMAN_REVIEW",
    "mla_satisfaction": "HUMAN_REVIEW",
    "voting_intention_ls_party": "HUMAN_REVIEW",
}


def test_synthetic_demo_shows_what_the_engine_decides():
    model = build_synthetic()
    questions = {q["tag"]: q for q in model["questions"]}

    for tag, action in EXPECTED_ACTIONS.items():
        assert questions[tag]["action"] == action, tag

    assert questions["state_govt_change"]["question"]["action"] == "AUTO_FILL"
    assert questions["mla_choice"]["question"]["action"] == "PREFILL"
    assert questions["vs_past_candidate"]["question"]["named_options"] == ["रमेश चंद्र"]
    assert model["summary"]["agreement"]["disagree"] == 0
    assert model["synthetic"] is True


def test_script_words_follow_the_matcher_for_split_compounds():
    words = _script_words("विधान सभा चुनाव में", set(tokens("विधानसभा चुनाव")), heard_wh=False)

    assert [(w["text"], w["state"]) for w in words] == [
        ("विधान", "matched"), ("सभा", "matched"), ("चुनाव", "matched"), ("में", "filler"),
    ]


def test_committed_demo_data_is_current():
    committed = Path("demo/demo-data.js").read_text(encoding="utf-8")
    payload = json.loads(committed[committed.index("=") + 1:].strip().rstrip(";"))

    assert payload == json.loads(json.dumps(build_synthetic(), ensure_ascii=False)), (
        "Run: python -m scripts.build_demo --synthetic"
    )
