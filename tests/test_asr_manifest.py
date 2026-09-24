import json

import pytest

from src.asr.manifest import (
    ASRChunkRecord,
    ASRManifest,
    load_asr_manifest,
    save_asr_manifest,
)


def test_valid_manifest():
    manifest = ASRManifest(
        audio_id="test-audio",
        model_name="test-model",
        chunks=[
            ASRChunkRecord(
                chunk_id="chunk_00",
                start_sec=0,
                end_sec=17,
                text="नमस्कार",
            ),
            ASRChunkRecord(
                chunk_id="chunk_01",
                start_sec=15,
                end_sec=32,
                text="अगला सवाल",
            ),
        ],
    )

    assert manifest.audio_id == "test-audio"
    assert len(manifest.chunks) == 2


def test_invalid_chunk_timing_fails():
    with pytest.raises(
        ValueError
    ):
        ASRChunkRecord(
            chunk_id="chunk_00",
            start_sec=20,
            end_sec=10,
            text="test",
        )


def test_manifest_save_and_load(
    tmp_path,
):
    manifest = ASRManifest(
        audio_id="test-audio",
        model_name="test-model",
        chunks=[
            ASRChunkRecord(
                chunk_id="chunk_00",
                start_sec=0,
                end_sec=17,
                text="नमस्कार",
            ),
        ],
    )

    path = (
        tmp_path
        / "manifest.json"
    )

    save_asr_manifest(
        manifest,
        path,
    )

    loaded = load_asr_manifest(
        path
    )

    assert loaded == manifest


def test_manifest_preserves_hindi(
    tmp_path,
):
    manifest = ASRManifest(
        audio_id="test-audio",
        model_name="Vaani",
        chunks=[
            ASRChunkRecord(
                chunk_id="chunk_00",
                start_sec=0,
                end_sec=17,
                text="मुझे पता नहीं",
            ),
        ],
    )

    path = (
        tmp_path
        / "manifest.json"
    )

    save_asr_manifest(
        manifest,
        path,
    )

    raw = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        raw["chunks"][0]["text"]
        == "मुझे पता नहीं"
    )