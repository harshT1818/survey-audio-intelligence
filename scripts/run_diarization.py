import argparse
import json
from pathlib import Path

from src.diarization.pyannote_runner import (
    diarize_audio,
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "audio_path"
    )

    parser.add_argument(
        "--audio-id",
        default="manual_dialogue_test_01",
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
        default=(
            "data/private/manual/"
            "manual_dialogue_test_01_"
            "diarization.json"
        ),
    )

    args = parser.parse_args()

    result = diarize_audio(
        audio_path=args.audio_path,
        audio_id=args.audio_id,
        min_speakers=args.min_speakers,
        max_speakers=args.max_speakers,
    )

    print()
    print("=== DIARIZATION ===")
    print()

    for segment in result.segments:
        print(
            f"{segment.speaker_id:12} "
            f"{segment.start_sec:6.2f} "
            f"→ "
            f"{segment.end_sec:6.2f}"
        )

    output_path = Path(
        args.output
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output_path,
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
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()