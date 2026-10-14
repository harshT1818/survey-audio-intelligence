import argparse
import json
from pathlib import Path

from src.diarization.pyannote_runner import (
    diarize_audio,
)


def build_default_output_path(
    audio_path: str | Path,
) -> Path:
    audio_path = Path(
        audio_path
    )

    return (
        audio_path.parent
        / (
            f"{audio_path.stem}"
            "_diarization.json"
        )
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "audio_path",
        help=(
            "Path to the audio file "
            "to diarize."
        ),
    )

    parser.add_argument(
        "--audio-id",
        default=None,
        help=(
            "Optional identifier for "
            "the audio. Defaults to "
            "the input filename stem."
        ),
    )

    parser.add_argument(
        "--min-speakers",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--max-speakers",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional output JSON path. "
            "Defaults to "
            "<audio>_diarization.json "
            "beside the source audio."
        ),
    )

    args = parser.parse_args()

    audio_path = Path(
        args.audio_path
    )

    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio file not found: "
            f"{audio_path}"
        )

    audio_id = (
        args.audio_id
        if args.audio_id
        else audio_path.stem
    )

    output_path = (
        Path(args.output)
        if args.output
        else build_default_output_path(
            audio_path
        )
    )

    result = diarize_audio(
        audio_path=str(
            audio_path
        ),
        audio_id=audio_id,
        min_speakers=(
            args.min_speakers
        ),
        max_speakers=(
            args.max_speakers
        ),
    )

    print()
    print(
        "=== DIARIZATION ==="
    )
    print()

    for segment in result.segments:
        print(
            f"{segment.speaker_id:12} "
            f"{segment.start_sec:6.2f} "
            f"→ "
            f"{segment.end_sec:6.2f}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result.model_dump(),
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"Audio ID: {audio_id}"
    )

    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()