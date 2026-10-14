from src.full_sample.dialogue_segments import (
    build_question_dialogue_segments,
    clip_interval,
    normalize_diarization_segments,
    overlap_sec,
)


def test_overlap():
    assert (
        overlap_sec(
            10.0,
            20.0,
            15.0,
            25.0,
        )
        == 5.0
    )


def test_no_overlap():
    assert (
        overlap_sec(
            10.0,
            20.0,
            21.0,
            25.0,
        )
        == 0.0
    )


def test_clip_interval():
    assert (
        clip_interval(
            start_sec=8.0,
            end_sec=12.0,
            clip_start_sec=10.0,
            clip_end_sec=20.0,
        )
        == (
            10.0,
            12.0,
        )
    )


def test_normalize_segments():
    payload = {
        "segments": [
            {
                "speaker_id": (
                    "SPEAKER_00"
                ),
                "start_sec": 1.0,
                "end_sec": 2.0,
            }
        ]
    }

    result = (
        normalize_diarization_segments(
            payload
        )
    )

    assert len(result) == 1

    assert (
        result[0]["speaker_id"]
        == "SPEAKER_00"
    )

    assert (
        result[0]["duration_sec"]
        == 1.0
    )


def test_question_intersection():
    questions = [
        {
            "question_index": 1,
            "tag": "test_question",
            "question_text": "Question",
            "stored_response": "Yes",
            "asr_status": "COMPLETE",
            "transcript": "Question yes",
            "start_sec": 10.0,
            "end_sec": 20.0,
        }
    ]

    diarization = {
        "segments": [
            {
                "speaker_id": (
                    "SPEAKER_00"
                ),
                "start_sec": 8.8,
                "end_sec": 12.0,
            },
            {
                "speaker_id": (
                    "SPEAKER_01"
                ),
                "start_sec": 12.5,
                "end_sec": 14.0,
            },
            {
                "speaker_id": (
                    "SPEAKER_00"
                ),
                "start_sec": 20.5,
                "end_sec": 21.0,
            },
        ]
    }

    result = (
        build_question_dialogue_segments(
            questions=questions,
            diarization_payload=(
                diarization
            ),
            context_before_sec=1.5,
            context_after_sec=1.5,
        )
    )

    assert len(result) == 1

    question = result[0]

    assert (
        question[
            "speaker_count_in_core"
        ]
        == 2
    )

    assert (
        question[
            "speakers_in_core"
        ]
        == [
            "SPEAKER_00",
            "SPEAKER_01",
        ]
    )

    assert (
        len(
            question["segments"]
        )
        == 3
    )

    assert (
        question[
            "segments"
        ][0][
            "core_overlap_sec"
        ]
        == 2.0
    )

    assert (
        question[
            "segments"
        ][2][
            "region"
        ]
        == "context_after"
    )


def test_micro_segment_preserved():
    questions = [
        {
            "question_index": 1,
            "tag": "test",
            "start_sec": 0.0,
            "end_sec": 2.0,
        }
    ]

    diarization = {
        "segments": [
            {
                "speaker_id": (
                    "SPEAKER_01"
                ),
                "start_sec": 1.0,
                "end_sec": 1.05,
            }
        ]
    }

    result = (
        build_question_dialogue_segments(
            questions=questions,
            diarization_payload=(
                diarization
            ),
        )
    )

    segment = (
        result[0][
            "segments"
        ][0]
    )

    assert (
        segment[
            "micro_segment"
        ]
        is True
    )