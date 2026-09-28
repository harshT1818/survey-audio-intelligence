import json
from pathlib import Path

from src.audio.segment_refinement import (
    RefinedClip,
    RefinementManifest,
    build_split_intervals,
    find_silence_split_points,
    padded_interval,
    read_pcm16_mono_wav,
    save_refinement_manifest,
    write_wav_clip,
)


SOURCE_AUDIO = Path(
    "data/private/manual/"
    "manual_dialogue_test_01_16k.wav"
)

CLIP_MANIFEST_PATH = Path(
    "data/private/manual/"
    "manual_dialogue_test_01_speaker_clips.json"
)

OUTPUT_DIRECTORY = Path(
    "data/private/manual/"
    "refined_clips"
)

OUTPUT_MANIFEST = Path(
    "data/private/manual/"
    "manual_dialogue_test_01_"
    "refined_clips.json"
)


# These clips mostly need slightly more
# acoustic context for a better ASR pass.
PADDED_RETRANSCRIBE_IDS = {
    "segment_015_SPEAKER_00",
    "segment_016_SPEAKER_01",
    "segment_020_SPEAKER_00",
    "segment_021_SPEAKER_01",
    "segment_023_SPEAKER_00",
}


# These clips contain multiple actual
# dialogue turns and should be split
# around real acoustic pauses.
SPLIT_IDS = {
    "segment_019_SPEAKER_00",
    "segment_028_SPEAKER_00",
}


def load_json(
    path: Path,
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main():
    if not SOURCE_AUDIO.exists():
        raise FileNotFoundError(
            f"Missing source audio: "
            f"{SOURCE_AUDIO}"
        )

    if not CLIP_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            (
                "Missing speaker clip manifest: "
                f"{CLIP_MANIFEST_PATH}"
            )
        )

    (
        samples,
        sample_rate,
    ) = read_pcm16_mono_wav(
        SOURCE_AUDIO
    )

    audio_duration_sec = (
        len(samples)
        / sample_rate
    )

    source_manifest = load_json(
        CLIP_MANIFEST_PATH
    )

    clips_by_id = {
        clip["clip_id"]: clip
        for clip in source_manifest[
            "clips"
        ]
    }

    refined_clips = []

    print()
    print(
        "=== SEGMENT REFINEMENT ==="
    )
    print()

    for clip_id in sorted(
        PADDED_RETRANSCRIBE_IDS
    ):
        source = clips_by_id.get(
            clip_id
        )

        if source is None:
            print(
                f"Missing: {clip_id}"
            )
            continue

        (
            start_sec,
            end_sec,
        ) = padded_interval(
            start_sec=source[
                "start_sec"
            ],
            end_sec=source[
                "end_sec"
            ],
            audio_duration_sec=(
                audio_duration_sec
            ),
            padding_sec=0.20,
        )

        refined_id = (
            f"{clip_id}_context"
        )

        output_path = (
            OUTPUT_DIRECTORY
            / f"{refined_id}.wav"
        )

        write_wav_clip(
            samples=samples,
            sample_rate=sample_rate,
            start_sec=start_sec,
            end_sec=end_sec,
            destination=output_path,
        )

        refined_clips.append(
            RefinedClip(
                clip_id=refined_id,
                source_segment_id=(
                    clip_id
                ),
                start_sec=start_sec,
                end_sec=end_sec,
                reason=(
                    "padded_retranscription"
                ),
                clip_path=str(
                    output_path
                ),
            )
        )

        print(
            f"{refined_id:40} "
            f"{start_sec:6.2f} "
            f"→ {end_sec:6.2f} "
            f"PADDED"
        )

    for clip_id in sorted(
        SPLIT_IDS
    ):
        source = clips_by_id.get(
            clip_id
        )

        if source is None:
            print(
                f"Missing: {clip_id}"
            )
            continue

        start_sec = source[
            "start_sec"
        ]

        end_sec = source[
            "end_sec"
        ]

        start_sample = int(
            start_sec
            * sample_rate
        )

        end_sample = int(
            end_sec
            * sample_rate
        )

        segment_samples = samples[
            start_sample:end_sample
        ]

        split_points = (
            find_silence_split_points(
                samples=segment_samples,
                sample_rate=sample_rate,
                min_silence_sec=0.16,
                threshold_quantile=0.22,
            )
        )

        intervals = (
            build_split_intervals(
                segment_start_sec=(
                    start_sec
                ),
                segment_end_sec=(
                    end_sec
                ),
                split_points_local_sec=(
                    split_points
                ),
                min_piece_sec=0.45,
            )
        )

        print()
        print(
            f"{clip_id}"
        )

        print(
            f"  silence splits: "
            f"{[
                round(point, 2)
                for point
                in split_points
            ]}"
        )

        for index, (
            interval_start,
            interval_end,
        ) in enumerate(
            intervals
        ):
            refined_id = (
                f"{clip_id}_"
                f"part_{index:02d}"
            )

            output_path = (
                OUTPUT_DIRECTORY
                / f"{refined_id}.wav"
            )

            write_wav_clip(
                samples=samples,
                sample_rate=sample_rate,
                start_sec=(
                    interval_start
                ),
                end_sec=(
                    interval_end
                ),
                destination=(
                    output_path
                ),
            )

            refined_clips.append(
                RefinedClip(
                    clip_id=(
                        refined_id
                    ),
                    source_segment_id=(
                        clip_id
                    ),
                    start_sec=(
                        interval_start
                    ),
                    end_sec=(
                        interval_end
                    ),
                    reason=(
                        "silence_split"
                    ),
                    clip_path=str(
                        output_path
                    ),
                )
            )

            print(
                f"  "
                f"{refined_id:38} "
                f"{interval_start:6.2f} "
                f"→ "
                f"{interval_end:6.2f}"
            )

    manifest = RefinementManifest(
        audio_id=(
            "manual_dialogue_test_01"
        ),
        source_audio=str(
            SOURCE_AUDIO
        ),
        clips=refined_clips,
    )

    save_refinement_manifest(
        manifest=manifest,
        file_path=OUTPUT_MANIFEST,
    )

    print()
    print(
        "=" * 70
    )

    print(
        f"Refined clips: "
        f"{len(refined_clips)}"
    )

    print(
        f"Manifest: "
        f"{OUTPUT_MANIFEST}"
    )


if __name__ == "__main__":
    main()