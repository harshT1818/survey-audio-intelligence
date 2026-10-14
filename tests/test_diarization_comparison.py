import pytest

from src.diarization.comparison import (
    agent_speaker,
    compare_diarization,
    score_checkpoint,
    speaker_seconds,
)


def seg(speaker, start, end):
    return {"speaker_id": speaker, "start_sec": start, "end_sec": end}


# Synthetic timeline: A asks (0-10), B answers (10-12),
# A asks again (12-20) and the answer at 18-20 is wrongly A.
SEGMENTS = [seg("A", 0, 10), seg("B", 10, 12), seg("A", 12, 20)]

CHECKPOINTS = [
    {"label": "intro", "expected": "agent", "start_sec": 0, "end_sec": 8},
    {"label": "answer ok", "expected": "respondent", "start_sec": 10, "end_sec": 12},
    {"label": "q then a", "expected": "mixed", "start_sec": 9, "end_sec": 11},
    {"label": "answer lost", "expected": "respondent", "start_sec": 18, "end_sec": 20},
    {"label": "unclear", "expected": "respondent", "start_sec": 14, "end_sec": 15, "unsure": True},
]


def test_speaker_seconds_clips_to_range():
    assert speaker_seconds(SEGMENTS, 9, 11) == {"A": 1.0, "B": 1.0}


def test_agent_speaker_comes_from_agent_checkpoints():
    assert agent_speaker(SEGMENTS, CHECKPOINTS) == "A"


def test_compare_scores_checkpoints_and_skips_unsure():
    report = compare_diarization({"model_name": "m", "segments": SEGMENTS}, CHECKPOINTS)

    verdicts = {c["label"]: c["verdict"] for c in report["checkpoints"]}
    assert verdicts == {
        "intro": "PASS",
        "answer ok": "PASS",
        "q then a": "PASS",
        "answer lost": "FAIL",
        "unclear": "FAIL",
    }
    assert report["scored"] == 4
    assert report["passed"] == 3
    assert report["speaker_totals_sec"] == {"A": 18.0, "B": 2.0}


def test_mixed_needs_both_speakers():
    result = score_checkpoint(
        {"expected": "mixed", "start_sec": 12, "end_sec": 16}, SEGMENTS, "A",
    )
    assert result["verdict"] == "FAIL"


def test_range_without_speech_is_not_a_pass():
    result = score_checkpoint(
        {"expected": "respondent", "start_sec": 30, "end_sec": 31}, SEGMENTS, "A",
    )
    assert result["verdict"] == "NO_SPEECH"


def test_unknown_expectation_is_rejected():
    with pytest.raises(ValueError):
        score_checkpoint({"expected": "maybe", "start_sec": 0, "end_sec": 1}, SEGMENTS, "A")
