import pytest

from src.full_sample.asr_batch import (
    find_question_overlaps,
    interval_overlap_sec,
    split_duration,
)


def test_non_overlapping_intervals():
    result = interval_overlap_sec(
        0,
        10,
        11,
        20,
    )

    assert result == 0.0


def test_overlapping_intervals():
    result = interval_overlap_sec(
        385.449,
        453.214,
        406.689,
        454.445,
    )

    assert result == 46.525


def test_short_audio_is_single_chunk():
    result = split_duration(
        duration_sec=12.0,
    )

    assert result == [
        (
            0.0,
            12.0,
        )
    ]


def test_long_audio_is_split_with_overlap():
    result = split_duration(
        duration_sec=49.0,
        max_chunk_sec=20.0,
        overlap_sec=2.0,
    )

    assert result == [
        (
            0.0,
            20.0,
        ),
        (
            18.0,
            38.0,
        ),
        (
            36.0,
            49.0,
        ),
    ]


def test_tiny_tail_is_absorbed():
    result = split_duration(
        duration_sec=39.0,
        max_chunk_sec=20.0,
        overlap_sec=2.0,
        minimum_tail_sec=3.0,
    )

    assert result == [
        (
            0.0,
            20.0,
        ),
        (
            18.0,
            39.0,
        ),
    ]


def test_invalid_overlap():
    with pytest.raises(
        ValueError
    ):
        split_duration(
            duration_sec=40,
            max_chunk_sec=20,
            overlap_sec=20,
        )


def test_find_question_overlaps():
    questions = [
        {
            "tag": "first",
            "start_sec": 10.0,
            "end_sec": 20.0,
        },
        {
            "tag": "second",
            "start_sec": 18.0,
            "end_sec": 25.0,
        },
        {
            "tag": "third",
            "start_sec": 30.0,
            "end_sec": 40.0,
        },
    ]

    result = find_question_overlaps(
        questions
    )

    assert result["first"] == [
        {
            "tag": "second",
            "overlap_sec": 2.0,
        }
    ]

    assert result["second"] == [
        {
            "tag": "first",
            "overlap_sec": 2.0,
        }
    ]

    assert result["third"] == []