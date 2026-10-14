import argparse

from src.diarization.clip_export import (
    export_speaker_clips,
    load_diarization_result,
    save_speaker_clip_manifest,
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "audio_path"
    )

    parser.add_argument(
        "diarization_path"
    )

    parser.add_argument(
        "--output-dir",
        default=(
            "data/private/manual/"
            "diarization_clips"
        ),
    )

    parser.add_argument(
        "--manifest",
        default=(
            "data/private/manual/"
            "manual_dialogue_test_01_"
            "speaker_clips.json"
        ),
    )

    parser.add_argument(
        "--max-gap",
        type=float,
        default=0.5,
    )

    parser.add_argument(
        "--min-duration",
        type=float,
        default=0.25,
    )

    args = parser.parse_args()

    diarization = (
        load_diarization_result(
            args.diarization_path
        )
    )

    manifest = export_speaker_clips(
        source_audio=args.audio_path,
        diarization=diarization,
        output_directory=args.output_dir,
        max_gap_sec=args.max_gap,
        min_duration_sec=args.min_duration,
    )

    save_speaker_clip_manifest(
        manifest=manifest,
        file_path=args.manifest,
    )

    print()
    print(
        "=== SPEAKER CLIPS ==="
    )
    print()

    for clip in manifest.clips:
        duration = (
            clip.end_sec
            - clip.start_sec
        )

        print(
            f"{clip.clip_id:24} "
            f"{clip.start_sec:6.2f} "
            f"→ {clip.end_sec:6.2f} "
            f"({duration:5.2f}s)"
        )

    print()
    print(
        f"Total clips: "
        f"{len(manifest.clips)}"
    )

    print(
        f"Manifest: "
        f"{args.manifest}"
    )


if __name__ == "__main__":
    main()