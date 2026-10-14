import numpy as np

from src.audio.segment_refinement import (
    build_split_intervals,
    find_silence_split_points,
    padded_interval,
)


def test_padding_adds_context():
    start, end = padded_interval(
        start_sec=10.0,
        end_sec=11.0,
        audio_duration_sec=20.0,
        padding_sec=0.2,
    )

    assert start == 9.8
    assert end == 11.2


def test_padding_does_not_go_below_zero():
    start, end = padded_interval(
        start_sec=0.1,
        end_sec=1.0,
        audio_duration_sec=20.0,
        padding_sec=0.2,
    )

    assert start == 0.0
    assert end == 1.2


def test_padding_does_not_exceed_audio():
    start, end = padded_interval(
        start_sec=19.0,
        end_sec=19.9,
        audio_duration_sec=20.0,
        padding_sec=0.2,
    )

    assert start == 18.8
    assert end == 20.0


def test_detects_silence_between_two_speech_regions():
    sample_rate = 1000

    speech_1 = np.full(
        1000,
        5000,
        dtype=np.int16,
    )

    silence = np.zeros(
        300,
        dtype=np.int16,
    )

    speech_2 = np.full(
        1000,
        5000,
        dtype=np.int16,
    )

    samples = np.concatenate(
        [
            speech_1,
            silence,
            speech_2,
        ]
    )

    points = find_silence_split_points(
        samples=samples,
        sample_rate=sample_rate,
        min_silence_sec=0.15,
    )

    assert len(points) >= 1

    assert (
        0.9
        <= points[0]
        <= 1.4
    )


def test_build_split_intervals():
    intervals = build_split_intervals(
        segment_start_sec=10.0,
        segment_end_sec=15.0,
        split_points_local_sec=[
            2.0,
            3.5,
        ],
    )

    assert intervals == [
        (10.0, 12.0),
        (12.0, 13.5),
        (13.5, 15.0),
    ]


def test_tiny_pieces_are_not_created():
    intervals = build_split_intervals(
        segment_start_sec=10.0,
        segment_end_sec=12.0,
        split_points_local_sec=[
            0.1,
            1.0,
        ],
        min_piece_sec=0.45,
    )

    assert (
        (10.0, 10.1)
        not in intervals
    )