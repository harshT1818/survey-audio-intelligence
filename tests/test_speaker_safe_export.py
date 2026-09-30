from src.full_sample.speaker_safe_export import (
    speaker_safe_export_bounds,
)


def turn(
    index,
    speaker,
    role,
    start,
    end,
):
    return {
        "turn_index": index,
        "speaker_id": speaker,
        "role": role,
        "start_sec": start,
        "end_sec": end,
    }


def test_full_padding_without_other_speaker():
    current = turn(
        1,
        "S0",
        "agent",
        10.0,
        12.0,
    )

    result = (
        speaker_safe_export_bounds(
            turn=current,
            all_turns=[
                current
            ],
            padding_sec=0.20,
        )
    )

    assert (
        result[
            "export_start_sec"
        ]
        == 9.8
    )

    assert (
        result[
            "export_end_sec"
        ]
        == 12.2
    )

    assert (
        result[
            "padding_clipped_for_speaker"
        ]
        is False
    )


def test_padding_stops_at_next_other_speaker():
    current = turn(
        1,
        "S0",
        "agent",
        10.0,
        12.0,
    )

    respondent = turn(
        2,
        "S1",
        "respondent",
        12.1,
        13.0,
    )

    result = (
        speaker_safe_export_bounds(
            turn=current,
            all_turns=[
                current,
                respondent,
            ],
            padding_sec=0.20,
        )
    )

    assert (
        result[
            "export_start_sec"
        ]
        == 9.8
    )

    assert (
        result[
            "export_end_sec"
        ]
        == 12.1
    )

    assert (
        result[
            "actual_right_padding_sec"
        ]
        == 0.1
    )

    assert (
        result[
            "padding_clipped_for_speaker"
        ]
        is True
    )


def test_padding_stops_at_previous_other_speaker():
    respondent = turn(
        1,
        "S1",
        "respondent",
        9.0,
        9.9,
    )

    current = turn(
        2,
        "S0",
        "agent",
        10.0,
        12.0,
    )

    result = (
        speaker_safe_export_bounds(
            turn=current,
            all_turns=[
                respondent,
                current,
            ],
            padding_sec=0.20,
        )
    )

    assert (
        result[
            "export_start_sec"
        ]
        == 9.9
    )

    assert (
        result[
            "actual_left_padding_sec"
        ]
        == 0.1
    )


def test_raw_overlap_is_preserved_but_flagged():
    agent = turn(
        1,
        "S0",
        "agent",
        10.0,
        15.0,
    )

    respondent = turn(
        2,
        "S1",
        "respondent",
        13.0,
        14.0,
    )

    result = (
        speaker_safe_export_bounds(
            turn=respondent,
            all_turns=[
                agent,
                respondent,
            ],
            padding_sec=0.20,
        )
    )

    assert (
        result[
            "raw_cross_speaker_overlap"
        ]
        is True
    )

    assert (
        result[
            "raw_cross_speaker_overlap_sec"
        ]
        == 1.0
    )

    assert (
        result[
            "export_start_sec"
        ]
        == 13.0
    )

    assert (
        result[
            "export_end_sec"
        ]
        == 14.0
    )


def test_same_speaker_does_not_clip_padding():
    first = turn(
        1,
        "S0",
        "agent",
        10.0,
        12.0,
    )

    second = turn(
        2,
        "S0",
        "agent",
        12.1,
        13.0,
    )

    result = (
        speaker_safe_export_bounds(
            turn=first,
            all_turns=[
                first,
                second,
            ],
            padding_sec=0.20,
        )
    )

    assert (
        result[
            "export_end_sec"
        ]
        == 12.2
    )