from pathlib import Path

import pytest

from src.full_sample.audio_windows import (
    build_export_manifest_entry,
    build_window_filename,
    safe_filename,
    validate_window,
)


def test_safe_filename():
    assert (
        safe_filename(
            "state govt change"
        )
        == "state_govt_change"
    )


def test_safe_filename_keeps_valid_tag():
    assert (
        safe_filename(
            "state_govt_change"
        )
        == "state_govt_change"
    )


def test_window_filename():
    assert (
        build_window_filename(
            3,
            "major_problems",
        )
        == "003_major_problems.wav"
    )


def test_valid_window():
    validate_window(
        start_sec=10.0,
        end_sec=15.0,
    )


def test_negative_start_is_invalid():
    with pytest.raises(
        ValueError
    ):
        validate_window(
            start_sec=-1,
            end_sec=5,
        )


def test_equal_end_is_invalid():
    with pytest.raises(
        ValueError
    ):
        validate_window(
            start_sec=10,
            end_sec=10,
        )


def test_manifest_entry():
    window = {
        "tag": "age",
        "order": 7,
        "question_tag_id": 1087,
        "question_text": (
            "आपकी उम्र क्या है?"
        ),
        "question_type": (
            "subjective"
        ),
        "raw_response": "55",
        "english_value": [],
        "hindi_value": [],
        "regional_value": [],
        "others": {},
        "start_sec": 94.430,
        "end_sec": 97.626,
    }

    result = (
        build_export_manifest_entry(
            index=1,
            window=window,
            output_path=Path(
                "age.wav"
            ),
        )
    )

    assert (
        result["tag"]
        == "age"
    )

    assert (
        result["duration_sec"]
        == 3.196
    )

    assert (
        result["stored_response"]
        == "55"
    )