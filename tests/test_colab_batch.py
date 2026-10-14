import pytest

from src.full_sample.colab_batch import (
    combine_turn_manifests,
    diarization_response_id,
    split_asr_results,
)

A = "a" * 24
B = "b" * 24


def test_same_clip_name_in_two_samples_gets_distinct_batch_names():
    combined = combine_turn_manifests({
        A: [{"audio_file": "data\\private\\r2\\x\\001_age_turn_01.wav", "export_for_asr": True}],
        B: [{"audio_file": "/x/001_age_turn_01.wav", "export_for_asr": True}],
    })

    names = [row["audio_file"] for row in combined]

    assert names == [f"{A}__001_age_turn_01.wav", f"{B}__001_age_turn_01.wav"]
    assert {row["response_id"] for row in combined} == {A, B}


def test_skipped_rows_without_audio_are_kept_unchanged():
    combined = combine_turn_manifests({A: [{"audio_file": None, "export_for_asr": False}]})

    assert combined[0]["audio_file"] is None


def test_asr_results_return_to_their_sample_with_original_names():
    split = split_asr_results(
        [
            {"audio_file": f"{A}__001_age_turn_01.wav", "transcript": "पचपन"},
            {"audio_file": f"{B}__001_age_turn_01.wav", "transcript": ""},
        ],
        {A, B},
    )

    assert split[A] == [{"audio_file": "001_age_turn_01.wav", "transcript": "पचपन"}]
    assert split[B] == [{"audio_file": "001_age_turn_01.wav", "transcript": ""}]


def test_result_from_another_batch_is_refused():
    with pytest.raises(ValueError, match="not from this batch"):
        split_asr_results([{"audio_file": "001_age_turn_01.wav", "transcript": "x"}], {A})


def test_diarization_file_name_gives_response_id():
    assert diarization_response_id(f"{A}_diarization_sortformer.json") == A

    with pytest.raises(ValueError):
        diarization_response_id(f"{A}.json")
