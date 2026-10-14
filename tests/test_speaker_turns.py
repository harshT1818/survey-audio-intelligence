from src.full_sample.speaker_turns import (
    add_role_to_turns,
    mark_turn_exportability,
    merge_same_speaker_segments,
)


def make_segment(
    speaker,
    start,
    end,
    index,
):
    return {
        "segment_index": index,
        "speaker_id": speaker,
        "clipped_start_sec": start,
        "clipped_end_sec": end,
        "region": "core",
        "touches_core": True,
    }


def test_merges_nearby_same_speaker():
    segments = [
        make_segment(
            "SPEAKER_00",
            10.0,
            11.0,
            1,
        ),
        make_segment(
            "SPEAKER_00",
            11.3,
            12.0,
            2,
        ),
    ]

    result = (
        merge_same_speaker_segments(
            segments,
            max_gap_sec=0.5,
        )
    )

    assert len(result) == 1

    assert (
        result[0]["start_sec"]
        == 10.0
    )

    assert (
        result[0]["end_sec"]
        == 12.0
    )


def test_does_not_merge_different_speaker():
    segments = [
        make_segment(
            "SPEAKER_00",
            10.0,
            11.0,
            1,
        ),
        make_segment(
            "SPEAKER_01",
            11.1,
            12.0,
            2,
        ),
    ]

    result = (
        merge_same_speaker_segments(
            segments,
            max_gap_sec=0.5,
        )
    )

    assert len(result) == 2


def test_does_not_merge_large_gap():
    segments = [
        make_segment(
            "SPEAKER_00",
            10.0,
            11.0,
            1,
        ),
        make_segment(
            "SPEAKER_00",
            12.0,
            13.0,
            2,
        ),
    ]

    result = (
        merge_same_speaker_segments(
            segments,
            max_gap_sec=0.5,
        )
    )

    assert len(result) == 2


def test_adds_roles():
    turns = [
        {
            "speaker_id": (
                "SPEAKER_00"
            ),
            "start_sec": 1.0,
            "end_sec": 2.0,
            "duration_sec": 1.0,
        }
    ]

    roles = {
        "SPEAKER_00": {
            "role": "agent",
            "confidence": "STRONG",
        }
    }

    result = add_role_to_turns(
        turns,
        roles,
    )

    assert (
        result[0]["role"]
        == "agent"
    )


def test_short_turn_is_not_exported():
    turns = [
        {
            "speaker_id": (
                "SPEAKER_01"
            ),
            "duration_sec": 0.20,
        }
    ]

    result = (
        mark_turn_exportability(
            turns,
            minimum_duration_sec=0.35,
        )
    )

    assert (
        result[0]["export_for_asr"]
        is False
    )

    assert (
        result[0]["skip_reason"]
        == "turn_too_short"
    )