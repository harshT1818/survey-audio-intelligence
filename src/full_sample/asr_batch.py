import subprocess
from pathlib import Path
from typing import Any


def interval_overlap_sec(
    start_a: float,
    end_a: float,
    start_b: float,
    end_b: float,
) -> float:
    start = max(
        start_a,
        start_b,
    )

    end = min(
        end_a,
        end_b,
    )

    return round(
        max(
            0.0,
            end - start,
        ),
        3,
    )


def find_question_overlaps(
    questions: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    overlaps: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for index, left in enumerate(
        questions
    ):
        left_tag = str(
            left["tag"]
        )

        overlaps.setdefault(
            left_tag,
            [],
        )

        for right in questions[
            index + 1:
        ]:
            overlap_sec = (
                interval_overlap_sec(
                    float(
                        left["start_sec"]
                    ),
                    float(
                        left["end_sec"]
                    ),
                    float(
                        right["start_sec"]
                    ),
                    float(
                        right["end_sec"]
                    ),
                )
            )

            if overlap_sec <= 0:
                continue

            right_tag = str(
                right["tag"]
            )

            overlaps.setdefault(
                right_tag,
                [],
            )

            overlaps[
                left_tag
            ].append(
                {
                    "tag": right_tag,
                    "overlap_sec": (
                        overlap_sec
                    ),
                }
            )

            overlaps[
                right_tag
            ].append(
                {
                    "tag": left_tag,
                    "overlap_sec": (
                        overlap_sec
                    ),
                }
            )

    return overlaps


def split_duration(
    duration_sec: float,
    max_chunk_sec: float = 20.0,
    overlap_sec: float = 2.0,
    minimum_tail_sec: float = 3.0,
) -> list[tuple[float, float]]:
    if duration_sec <= 0:
        raise ValueError(
            "duration_sec must be positive."
        )

    if max_chunk_sec <= 0:
        raise ValueError(
            "max_chunk_sec must be positive."
        )

    if overlap_sec < 0:
        raise ValueError(
            "overlap_sec cannot be negative."
        )

    if overlap_sec >= max_chunk_sec:
        raise ValueError(
            "overlap_sec must be smaller "
            "than max_chunk_sec."
        )

    if duration_sec <= max_chunk_sec:
        return [
            (
                0.0,
                round(
                    duration_sec,
                    3,
                ),
            )
        ]

    intervals = []

    start = 0.0

    while start < duration_sec:
        end = min(
            start + max_chunk_sec,
            duration_sec,
        )

        remaining = (
            duration_sec - end
        )

        if (
            remaining > 0
            and remaining
            < minimum_tail_sec
        ):
            end = duration_sec

        intervals.append(
            (
                round(
                    start,
                    3,
                ),
                round(
                    end,
                    3,
                ),
            )
        )

        if end >= duration_sec:
            break

        start = (
            end
            - overlap_sec
        )

    return intervals


def export_audio_chunk(
    source_audio: Path,
    output_path: Path,
    start_sec: float,
    end_sec: float,
) -> None:
    if not source_audio.exists():
        raise FileNotFoundError(
            f"Missing source audio: "
            f"{source_audio}"
        )

    if (
        start_sec < 0
        or end_sec <= start_sec
    ):
        raise ValueError(
            "Invalid chunk interval."
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