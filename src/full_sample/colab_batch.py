"""Combine several samples into one Colab upload and split results back.

Turn clip names repeat across interviews, so batched clips are prefixed
with their response ID: "<response_id>__<clip name>".
"""

from typing import Any

from src.full_sample.prompting_dialogue import basename

PREFIX_SEPARATOR = "__"


def prefixed_clip_name(response_id: str, clip_name: str) -> str:
    return f"{response_id}{PREFIX_SEPARATOR}{clip_name}"


def split_prefixed_clip_name(
    name: str,
    response_ids: set[str],
) -> tuple[str, str]:
    response_id, separator, clip_name = name.partition(PREFIX_SEPARATOR)

    if not separator or not clip_name or response_id not in response_ids:
        raise ValueError(f"Clip name is not from this batch: {name}")

    return response_id, clip_name


def combine_turn_manifests(
    manifests: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """One manifest whose audio_file values match the batched clip names."""
    combined = []

    for response_id, rows in manifests.items():
        for row in rows:
            clip_name = basename(row.get("audio_file"))
            combined.append({
                **row,
                "response_id": response_id,
                "audio_file": (
                    prefixed_clip_name(response_id, clip_name)
                    if clip_name
                    else row.get("audio_file")
                ),
            })

    return combined


def split_asr_results(
    results: list[dict[str, Any]],
    response_ids: set[str],
) -> dict[str, list[dict[str, Any]]]:
    """Route batched ASR rows back to each sample with original clip names."""
    split: dict[str, list[dict[str, Any]]] = {
        response_id: [] for response_id in response_ids
    }

    for row in results:
        response_id, clip_name = split_prefixed_clip_name(
            basename(row.get("audio_file")) or "",
            response_ids,
        )
        split[response_id].append({**row, "audio_file": clip_name})

    return split


def diarization_response_id(
    file_name: str,
    suffix: str = "_diarization_sortformer.json",
) -> str:
    if not file_name.endswith(suffix):
        raise ValueError(f"Unexpected diarization file: {file_name}")
    return file_name[: -len(suffix)]
