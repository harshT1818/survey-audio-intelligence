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