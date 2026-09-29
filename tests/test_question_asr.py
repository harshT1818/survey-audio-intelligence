from src.full_sample.question_asr import (
    build_question_asr_records,
    merge_text_parts,
)


def test_merges_exact_overlap():
    result = merge_text_parts(
        [
            (
                "क्या आप राज्य सरकार "
                "में बदलाव"
            ),
            (
                "बदलाव देखना "
                "चाहते हैं"
            ),
        ]
    )

    assert result == (
        "क्या आप राज्य सरकार में "
        "बदलाव देखना चाहते हैं"
    )


def test_merge_keeps_non_overlapping_text():
    result = merge_text_parts(
        [
            "पहला हिस्सा",
            "दूसरा हिस्सा",
        ]
    )

    assert result == (
        "पहला हिस्सा दूसरा हिस्सा"
    )


def test_empty_parts_are_ignored():
    result = merge_text_parts(
        [
            "पहला",
            "",
            "दूसरा",
        ]
    )

    assert result == (
        "पहला दूसरा"
    )


def test_builds_question_record():
    questions = [
        {
            "index": 1,
            "tag": "age",
            "question_text": (
                "आपकी उम्र क्या है"
            ),
            "stored_response": "55",
            "english_value": [],
            "hindi_value": [],
            "start_sec": 10.0,
            "end_sec": 14.0,
            "duration_sec": 4.0,
        }
    ]

    batch = [
        {
            "question_index": 1,
            "chunk_index": 1,
            "audio_file": (
                "001_age_chunk_01.wav"
            ),
            "absolute_start_sec": 10.0,
            "absolute_end_sec": 14.0,
            "overlap_review_required": False,
        }
    ]

    results = [
        {
            "audio_file": (
                "001_age_chunk_01.wav"
            ),
            "transcript": (
                "आपकी उम्र क्या है "
                "पचपन"
            ),
        }
    ]

    records = (
        build_question_asr_records(
            questions=questions,
            batch_manifest=batch,
            asr_results=results,
        )
    )

    assert len(records) == 1

    assert (
        records[0]["tag"]
        == "age"
    )

    assert (
        records[0]["asr_status"]
        == "COMPLETE"
    )

    assert (
        records[0]["transcript"]
        == "आपकी उम्र क्या है पचपन"
    )


def test_missing_asr_is_partial():
    questions = [
        {
            "index": 1,
            "tag": "test",
            "question_text": "test",
            "stored_response": "yes",
            "english_value": [],
            "hindi_value": [],
            "start_sec": 0.0,
            "end_sec": 10.0,
            "duration_sec": 10.0,
        }
    ]

    batch = [
        {
            "question_index": 1,
            "chunk_index": 1,
            "audio_file": (
                "001_test_chunk_01.wav"
            ),
            "absolute_start_sec": 0.0,
            "absolute_end_sec": 5.0,
            "overlap_review_required": False,
        },
        {
            "question_index": 1,
            "chunk_index": 2,
            "audio_file": (
                "001_test_chunk_02.wav"
            ),
            "absolute_start_sec": 4.0,
            "absolute_end_sec": 10.0,
            "overlap_review_required": False,
        },
    ]

    results = [
        {
            "audio_file": (
                "001_test_chunk_01.wav"
            ),
            "transcript": "hello",
        }
    ]

    records = (
        build_question_asr_records(
            questions=questions,
            batch_manifest=batch,
            asr_results=results,
        )
    )

    assert (
        records[0]["asr_status"]
        == "PARTIAL"
    )

    assert (
        records[0][
            "missing_chunk_files"
        ]
        == [
            "001_test_chunk_02.wav"
        ]
    )