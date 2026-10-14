from src.full_sample.turn_safety import (
    decision_rejection_reasons,
    is_decision_safe,
    safe_turns_after,
    select_first_safe_turn_after,
)


def turn(
    role,
    start,
    end,
    text,
    *,
    raw_overlap=False,
    raw_overlap_sec=0.0,
    asr_status="COMPLETE",
):
    return {
        "role": role,
        "start_sec": start,
        "end_sec": end,
        "transcript": text,
        "asr_status": asr_status,
        "cross_speaker_overlap": False,
        "raw_cross_speaker_overlap": (
            raw_overlap
        ),
        "raw_cross_speaker_overlap_sec": (
            raw_overlap_sec
        ),
    }


def test_clean_turn_is_safe():
    item = turn(
        "respondent",
        10.0,
        11.0,
        "हाँ",
    )

    assert (
        is_decision_safe(
            item
        )
        is True
    )


def test_raw_overlap_is_rejected():
    item = turn(
        "respondent",
        10.0,
        11.0,
        "हाँ",
        raw_overlap=True,
        raw_overlap_sec=1.0,
    )

    reasons = (
        decision_rejection_reasons(
            item
        )
    )

    assert (
        "RAW_CROSS_SPEAKER_OVERLAP"
        in reasons
    )


def test_unsafe_first_respondent_is_skipped():
    turns = [
        turn(
            "respondent",
            10.0,
            11.0,
            "आप बताइए",
            raw_overlap=True,
            raw_overlap_sec=1.0,
        ),
        turn(
            "respondent",
            11.5,
            13.0,
            (
                "सही आदमी "
                "होना चाहिए"
            ),
        ),
    ]

    result = (
        select_first_safe_turn_after(
            turns=turns,
            start_sec=9.0,
            role="respondent",
        )
    )

    assert (
        result["turn"][
            "start_sec"
        ]
        == 11.5
    )

    assert len(
        result[
            "rejected"
        ]
    ) == 1


def test_skipped_short_is_not_safe():
    item = turn(
        "respondent",
        10.0,
        10.02,
        "",
        asr_status=(
            "SKIPPED_SHORT"
        ),
    )

    assert (
        is_decision_safe(
            item
        )
        is False
    )


def test_safe_agent_followups_exclude_overlap():
    turns = [
        turn(
            "agent",
            10.0,
            11.0,
            "पहला",
            raw_overlap=True,
            raw_overlap_sec=0.5,
        ),
        turn(
            "agent",
            12.0,
            13.0,
            "दूसरा",
        ),
    ]

    result = (
        safe_turns_after(
            turns=turns,
            start_sec=9.0,
            role="agent",
        )
    )

    assert len(
        result["accepted"]
    ) == 1

    assert (
        result["accepted"][0][
            "transcript"
        ]
        == "दूसरा"
    )

    assert len(
        result["rejected"]
    ) == 1