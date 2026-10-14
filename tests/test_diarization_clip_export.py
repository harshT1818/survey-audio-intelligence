from src.diarization.clip_export import (
    merge_speaker_segments,
)
from src.diarization.models import (
    DiarizationSegment,
)


def test_adjacent_same_speaker_segments_are_merged():
    segments = [
        DiarizationSegment(
            speaker_id="SPEAKER_00",
            start_sec=1.0,
            end_sec=2.0,
        ),
        DiarizationSegment(
            speaker_id="SPEAKER_00",
            start_sec=2.2,
            end_sec=3.0,
        ),
    ]

    result = merge_speaker_segments(
        segments,
        max_gap_sec=0.5,
    )

    assert len(result) == 1

    assert result[0].start_sec == 1.0
    assert result[0].end_sec == 3.0


def test_large_gap_is_not_merged():
    segments = [
        DiarizationSegment(
            speaker_id="SPEAKER_00",
            start_sec=1.0,
            end_sec=2.0,
        ),
        DiarizationSegment(
            speaker_id="SPEAKER_00",
            start_sec=3.0,
            end_sec=4.0,
        ),
    ]

    result = merge_speaker_segments(
        segments,
        max_gap_sec=0.5,
    )

    assert len(result) == 2


def test_different_speakers_are_not_merged():
    segments = [
        DiarizationSegment(
            speaker_id="SPEAKER_00",
            start_sec=1.0,
            end_sec=2.0,
        ),
        DiarizationSegment(
            speaker_id="SPEAKER_01",
            start_sec=2.1,
            end_sec=3.0,
        ),
    ]

    result = merge_speaker_segments(
        segments,
        max_gap_sec=0.5,
    )

    assert len(result) == 2


def test_tiny_segments_are_removed():
    segments = [
        DiarizationSegment(
            speaker_id="SPEAKER_00",
            start_sec=1.0,
            end_sec=1.1,
        ),
        DiarizationSegment(
            speaker_id="SPEAKER_01",
            start_sec=2.0,
            end_sec=3.0,
        ),
    ]

    result = merge_speaker_segments(
        segments,
        min_duration_sec=0.25,
    )

    assert len(result) == 1

    assert (
        result[0].speaker_id
        == "SPEAKER_01"
    )


def test_segments_are_sorted():
    segments = [
        DiarizationSegment(
            speaker_id="SPEAKER_01",
            start_sec=10.0,
            end_sec=11.0,
        ),
        DiarizationSegment(
            speaker_id="SPEAKER_00",
            start_sec=1.0,
            end_sec=2.0,
        ),
    ]

    result = merge_speaker_segments(
        segments
    )

    assert result[0].start_sec == 1.0
    assert result[1].start_sec == 10.0


def test_overlapping_different_speakers_are_preserved():
    segments = [
        DiarizationSegment(
            speaker_id="SPEAKER_00",
            start_sec=48.5,
            end_sec=50.1,
        ),
        DiarizationSegment(
            speaker_id="SPEAKER_01",
            start_sec=49.4,
            end_sec=50.0,
        ),
    ]

    result = merge_speaker_segments(
        segments
    )

    assert len(result) == 2