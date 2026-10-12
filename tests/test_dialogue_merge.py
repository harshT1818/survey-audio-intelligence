import pytest

from src.full_sample.dialogue_merge import (
    asr_coverage,
    coverage_blockers,
    merge_dialogues_by_tag,
)
from src.full_sample.prompting_dialogue import basename


def manifest_row(name, exported=True):
    return {
        "tag": "q",
        "export_for_asr": exported,
        "audio_file": f"data\\private\\r2\\sample\\clips\\{name}",
    }


def test_basename_splits_windows_and_posix_paths():
    assert basename("data\\private\\clips\\a.wav") == "a.wav"
    assert basename("/content/clips/b.wav") == "b.wav"
    assert basename(None) is None


def test_coverage_reports_missing_unexpected_duplicate_and_empty():
    manifest = [
        manifest_row("a.wav"),
        manifest_row("b.wav"),
        manifest_row("c.wav"),
        manifest_row("skipped.wav", exported=False),
    ]
    results = [
        {"audio_file": "a.wav", "transcript": "हाँ"},
        {"audio_file": "a.wav", "transcript": "हाँ"},
        {"audio_file": "b.wav", "transcript": "  "},
        {"audio_file": "extra.wav", "transcript": "x"},
    ]

    coverage = asr_coverage(manifest, results)

    assert coverage["expected"] == 3
    assert coverage["missing"] == ["c.wav"]
    assert coverage["unexpected"] == ["extra.wav"]
    assert coverage["duplicates"] == ["a.wav"]
    assert coverage["empty"] == ["b.wav"]
    assert coverage_blockers(coverage) == [
        "missing: 1", "unexpected: 1", "duplicates: 1",
    ]


def test_empty_transcripts_do_not_block_merge():
    coverage = asr_coverage(
        [manifest_row("a.wav")],
        [{"audio_file": "a.wav", "transcript": ""}],
    )

    assert coverage["empty"] == ["a.wav"]
    assert coverage_blockers(coverage) == []


def test_merge_orders_by_question_index_without_changing_dialogues():
    existing = [{"tag": "mla_choice", "question_index": 10, "turns": [{"x": 1}]}]
    additional = [
        {"tag": "cm_choice", "question_index": 24, "turns": []},
        {"tag": "gender", "question_index": 3, "turns": []},
    ]

    merged = merge_dialogues_by_tag(existing, additional)

    assert [item["tag"] for item in merged] == ["gender", "mla_choice", "cm_choice"]
    assert merged[1] is existing[0]


def test_merge_refuses_tag_already_in_existing_evidence():
    existing = [{"tag": "mla_choice", "question_index": 10}]
    additional = [{"tag": "mla_choice", "question_index": 10}]

    with pytest.raises(ValueError, match="Duplicate dialogue tag: mla_choice"):
        merge_dialogues_by_tag(existing, additional)


def test_merge_refuses_untagged_dialogue():
    with pytest.raises(ValueError, match="without a tag"):
        merge_dialogues_by_tag([], [{"question_index": 1}])
