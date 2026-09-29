import re
import subprocess
from pathlib import Path
from typing import Any


def safe_filename(
    value: str,
) -> str:
    value = value.strip()

    value = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        value,
    )

    value = value.strip("_")

    return value or "question"


def validate_window(
    start_sec: float,
    end_sec: float,
) -> None:
    if start_sec < 0:
        raise ValueError(
            "start_sec cannot be negative."
        )

    if end_sec <= start_sec:
        raise ValueError(
            "end_sec must be greater than start_sec."
        )


def build_window_filename(
    index: int,
    tag: str,
) -> str:
    safe_tag = safe_filename(tag)

    return (
        f"{index:03d}_"
        f"{safe_tag}.wav"
    )


def export_audio_window(
    source_audio: Path,
    output_path: Path,
    start_sec: float,
    end_sec: float,
) -> None:
    validate_window(
        start_sec=start_sec,
        end_sec=end_sec,
    )

    if not source_audio.exists():
        raise FileNotFoundError(
            f"Missing audio: {source_audio}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    duration_sec = (
        end_sec
        - start_sec
    )

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start_sec:.3f}",
        "-i",
        str(source_audio),
        "-t",
        f"{duration_sec:.3f}",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]

    subprocess.run(
        command,
        check=True,
    )


def build_export_manifest_entry(
    index: int,
    window: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    duration_sec = round(
        window["end_sec"]
        - window["start_sec"],
        3,
    )

    return {
        "index": index,
        "tag": window.get("tag"),
        "order": window.get("order"),
        "question_tag_id": (
            window.get(
                "question_tag_id"
            )
        ),
        "question_text": (
            window.get(
                "question_text"
            )
        ),
        "question_type": (
            window.get(
                "question_type"
            )
        ),
        "stored_response": (
            window.get(
                "raw_response"
            )
        ),
        "english_value": (
            window.get(
                "english_value"
            )
        ),
        "hindi_value": (
            window.get(
                "hindi_value"
            )
        ),
        "regional_value": (
            window.get(
                "regional_value"
            )
        ),
        "others": window.get(
            "others",
            {},
        ),
        "start_sec": (
            window["start_sec"]
        ),
        "end_sec": (
            window["end_sec"]
        ),
        "duration_sec": (
            duration_sec
        ),
        "audio_file": str(
            output_path
        ),
    }