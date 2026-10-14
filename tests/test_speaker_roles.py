from src.full_sample.speaker_roles import (
    collect_speaker_totals,
    infer_speaker_roles,
)


def make_question(
    tag,
    speaker_00,
    speaker_01,
):
    return {
        "tag": tag,
        "speaker_stats": [
            {
                "speaker_id": (
                    "SPEAKER_00"
                ),
                "core_speech_sec": (
                    speaker_00
                ),
            },
            {
                "speaker_id": (
                    "SPEAKER_01"
                ),
                "core_speech_sec": (
                    speaker_01
                ),
            },
        ],
    }


def test_collect_speaker_totals():
    questions = [
        make_question(
            "first",
            5.0,
            1.0,
        ),
        make_question(
            "second",
            4.0,
            2.0,
        ),
    ]

    result = (
        collect_speaker_totals(
            questions
        )
    )

    assert (
        result["SPEAKER_00"]
        == 9.0
    )

    assert (
        result["SPEAKER_01"]
        == 3.0
    )


def test_infers_agent_from_intro():
    questions = [
        make_question(
            "introduction",
            10.0,
            0.0,
        ),
        make_question(
            "phone_no",
            5.0,
            2.0,
        ),
        make_question(
            "state_govt_change",
            4.0,
            1.0,
        ),
        make_question(
            "cm_choice",
            4.0,
            1.0,
        ),
    ]

    result = (
        infer_speaker_roles(
            questions
        )
    )

    assert (
        result["status"]
        == "RESOLVED"
    )

    assert (
        result["roles"][
            "SPEAKER_00"
        ]["role"]
        == "agent"
    )

    assert (
        result["roles"][
            "SPEAKER_01"
        ]["role"]
        == "respondent"
    )

    assert (
        result["confidence"]
        == "STRONG"
    )


def test_unresolved_without_intro():
    questions = [
        make_question(
            "phone_no",
            5.0,
            2.0,
        )
    ]

    result = (
        infer_speaker_roles(
            questions
        )
    )

    assert (
        result["status"]
        == "UNRESOLVED"
    )


def with_extra_speaker(question, speaker_id, seconds):
    question["speaker_stats"].append(
        {
            "speaker_id": speaker_id,
            "core_speech_sec": seconds,
        }
    )
    return question


def test_extra_speakers_are_kept_unknown():
    questions = [
        make_question("introduction", 10.0, 0.0),
        with_extra_speaker(
            make_question("phone_no", 5.0, 4.0),
            "SPEAKER_02",
            1.0,
        ),
        make_question("state_govt_change", 4.0, 3.0),
        make_question("cm_choice", 4.0, 3.0),
    ]

    result = infer_speaker_roles(questions)

    assert result["status"] == "RESOLVED"
    assert result["roles"]["SPEAKER_00"]["role"] == "agent"
    assert result["roles"]["SPEAKER_01"]["role"] == "respondent"
    assert result["roles"]["SPEAKER_02"]["role"] == "unknown"
    assert any(
        item["type"] == "additional_speakers"
        for item in result["evidence"]
    )


def test_agent_only_if_no_respondent_dominates_extra_speaker():
    questions = [
        make_question("introduction", 10.0, 0.0),
        with_extra_speaker(
            make_question("phone_no", 5.0, 4.0),
            "SPEAKER_02",
            3.0,
        ),
    ]

    result = infer_speaker_roles(questions)

    assert result["status"] == "AGENT_ONLY"
    assert result["roles"]["SPEAKER_00"]["role"] == "agent"
    assert result["roles"]["SPEAKER_01"]["role"] == "unknown"
    assert result["roles"]["SPEAKER_02"]["role"] == "unknown"
    assert "respondent" not in {r["role"] for r in result["roles"].values()}


def test_unresolved_if_intro_is_ambiguous():
    questions = [
        make_question(
            "introduction",
            5.0,
            3.0,
        ),
        make_question(
            "phone_no",
            5.0,
            2.0,
        ),
    ]

    result = (
        infer_speaker_roles(
            questions
        )
    )

    assert (
        result["status"]
        == "UNRESOLVED"
    )

def test_human_agent_label_replaces_ambiguous_introduction():
    questions = [
        make_question("introduction", 5.0, 4.8),
        make_question("phone_no", 2.0, 9.0),
        make_question("state_govt_change", 2.0, 6.0),
    ]

    assert infer_speaker_roles(questions)["status"] == "UNRESOLVED"

    result = infer_speaker_roles(questions, agent_speaker="SPEAKER_00")

    assert result["status"] == "RESOLVED"
    assert result["roles"]["SPEAKER_00"]["role"] == "agent"
    assert result["roles"]["SPEAKER_01"]["role"] == "respondent"
    assert result["evidence"][0]["type"] == "human_agent_label"


def test_unknown_agent_label_is_refused():
    import pytest

    with pytest.raises(ValueError, match="Unknown agent speaker"):
        infer_speaker_roles(
            [make_question("introduction", 5.0, 1.0)],
            agent_speaker="SPEAKER_09",
        )
