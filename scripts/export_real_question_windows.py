import argparse
import json
from pathlib import Path

from src.full_sample.audio_windows import (
    build_export_manifest_entry,
    build_window_filename,
    export_audio_window,
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--response-id",
        required=True,
    )

    args = parser.parse_args()

    sample_dir = (
        Path("data/private/r2")
        / args.response_id
    )

    audio_path = (
        sample_dir
        / "interview_16k_mono.wav"
    )

    windows_path = (
        sample_dir
        / "question_windows.json"
    )

    output_dir = (
        sample_dir
        / "question_audio"
    )

    manifest_path = (
        sample_dir
        / "question_audio_manifest.json"
    )

    if not audio_path.exists():
        raise FileNotFoundError(
            f"Missing audio: {audio_path}"
        )

    if not windows_path.exists():
        raise FileNotFoundError(
            f"Missing windows: {windows_path}"
        )

    windows = json.loads(
        windows_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        windows,
        list,
    ):
        raise ValueError(
            "question_windows.json "
            "must contain a JSON list."
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest = []

    print()
    print(
        "=== EXPORTING REAL "
        "QUESTION WINDOWS ==="
    )
    print()

    print(
        f"Response ID: "
        f"{args.response_id}"
    )

    print(
        f"Windows:     "
        f"{len(windows)}"
    )

    print()

    for (
        index,
        window,
    ) in enumerate(
        windows,
        start=1,
    ):
        tag = (
            window.get("tag")
            or f"question_{index}"
        )

        start_sec = float(
            window["start_sec"]
        )

        end_sec = float(
            window["end_sec"]
        )

        filename = (
            build_window_filename(
                index=index,
                tag=tag,
            )
        )

        output_path = (
            output_dir
            / filename
        )

        export_audio_window(
            source_audio=audio_path,
            output_path=output_path,
            start_sec=start_sec,
            end_sec=end_sec,
        )

        manifest_entry = (
            build_export_manifest_entry(
                index=index,
                window=window,
                output_path=(
                    output_path
                ),
            )
        )

        manifest.append(
            manifest_entry
        )

        print(
            f"[{index:02d}/"
            f"{len(windows):02d}] "
            f"{tag:35} "
            f"{start_sec:8.3f}s "
            f"→ "
            f"{end_sec:8.3f}s "
            f"("
            f"{end_sec - start_sec:6.2f}s"
            f")"
        )

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    total_duration_sec = sum(
        item["duration_sec"]
        for item in manifest
    )

    shortest = min(
        manifest,
        key=lambda item: (
            item["duration_sec"]
        ),
        default=None,
    )

    longest = max(
        manifest,
        key=lambda item: (
            item["duration_sec"]
        ),
        default=None,
    )

    print()
    print(
        "=== EXPORT COMPLETE ==="
    )
    print()

    print(
        f"Clips exported:       "
        f"{len(manifest)}"
    )

    print(
        f"Total question audio: "
        f"{total_duration_sec:.2f}s"
    )

    if shortest:
        print(
            f"Shortest:             "
            f"{shortest['tag']} "
            f"({shortest['duration_sec']:.2f}s)"
        )

    if longest:
        print(
            f"Longest:              "
            f"{longest['tag']} "
            f"({longest['duration_sec']:.2f}s)"
        )

    print()
    print(
        f"Audio directory: "
        f"{output_dir}"
    )

    print(
        f"Manifest:        "
        f"{manifest_path}"
    )


if __name__ == "__main__":
    main()