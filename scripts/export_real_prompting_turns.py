import argparse
import json
import subprocess
from pathlib import Path

from src.full_sample.speaker_safe_export import (
    speaker_safe_export_bounds,
)
from src.full_sample.speaker_turns import (
    add_role_to_turns,
    mark_turn_exportability,
    merge_same_speaker_segments,
)


DEFAULT_TAGS = [
    "state_govt_change",
    "state_govt_change_party",
    "mla_choice",
    "second_mla_choice_new",
    "cm_choice",
]


def load_json(
    path: Path,
):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def export_clip(
    source_audio: Path,
    output_path: Path,
    start_sec: float,
    end_sec: float,
) -> None:
    duration = (
        end_sec - start_sec
    )

    if duration <= 0:
        raise ValueError(
            "Invalid audio interval."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
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
        f"{duration:.3f}",
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


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--response-id",
        required=True,
    )

    parser.add_argument(
        "--max-gap-sec",
        type=float,
        default=0.60,
    )

    parser.add_argument(
        "--minimum-turn-sec",
        type=float,
        default=0.35,
    )

    parser.add_argument(
        "--padding-sec",
        type=float,
        default=0.20,
    )

    parser.add_argument(
        "--tags",
        nargs="*",
        default=DEFAULT_TAGS,
    )

    parser.add_argument(
        "--output-dir-name",
        default="prompting_turn_audio",
    )

    parser.add_argument(
        "--manifest-name",
        default=(
            "prompting_turn_manifest.json"
        ),
    )

    args = parser.parse_args()

    sample_dir = (
        Path("data/private/r2")
        / args.response_id
    )

    dialogue_path = (
        sample_dir
        / "question_dialogue_segments.json"
    )

    roles_path = (
        sample_dir
        / "speaker_roles.json"
    )

    audio_path = (
        sample_dir
        / "interview_16k_mono.wav"
    )

    questions = load_json(
        dialogue_path
    )

    roles_payload = load_json(
        roles_path
    )

    if (
        roles_payload.get(
            "status"
        )
        != "RESOLVED"
    ):
        raise ValueError(
            "Speaker roles are not resolved."
        )

    roles = roles_payload[
        "roles"
    ]

    by_tag = {
        question["tag"]: question
        for question in questions
    }

    output_dir = (
        sample_dir
        / args.output_dir_name
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest = []

    print()
    print(
        "=== PROMPTING TURN EXPORT ==="
    )
    print()

    print(
        f"Response ID: "
        f"{args.response_id}"
    )

    print(
        f"Tags:        "
        f"{len(args.tags)}"
    )

    print(
        f"Max gap:     "
        f"{args.max_gap_sec:.3f}s"
    )

    print(
        f"Padding:     "
        f"{args.padding_sec:.3f}s"
    )

    print(
        f"Output dir:  "
        f"{args.output_dir_name}"
    )

    print()

    for tag in args.tags:
        question = by_tag.get(
            tag
        )

        if question is None:
            print(
                f"WARNING: missing tag "
                f"{tag}"
            )
            continue

        turns = (
            merge_same_speaker_segments(
                question.get(
                    "segments",
                    [],
                ),
                max_gap_sec=(
                    args.max_gap_sec
                ),
            )
        )

        turns = add_role_to_turns(
            turns,
            roles,
        )

        turns = (
            mark_turn_exportability(
                turns,
                minimum_duration_sec=(
                    args.minimum_turn_sec
                ),
            )
        )

        print(tag)

        exported_for_question = 0

        for turn in turns:
            bounds = (
                speaker_safe_export_bounds(
                    turn=turn,
                    all_turns=turns,
                    padding_sec=(
                        args.padding_sec
                    ),
                )
            )

            export_start = float(
                bounds[
                    "export_start_sec"
                ]
            )

            export_end = float(
                bounds[
                    "export_end_sec"
                ]
            )

            record = {
                "response_id": (
                    args.response_id
                ),
                "tag": tag,
                "question_index": (
                    question[
                        "question_index"
                    ]
                ),
                "question_text": (
                    question.get(
                        "question_text"
                    )
                ),
                "stored_response": (
                    question.get(
                        "stored_response"
                    )
                ),
                **turn,
                **bounds,
                # Keep old names for downstream
                # compatibility.
                "padded_start_sec": (
                    export_start
                ),
                "padded_end_sec": (
                    export_end
                ),
                "audio_file": None,
            }

            if turn[
                "export_for_asr"
            ]:
                filename = (
                    f"{question['question_index']:03d}_"
                    f"{tag}_"
                    f"turn_{turn['turn_index']:02d}_"
                    f"{turn['role']}_"
                    f"{turn['speaker_id']}.wav"
                )

                output_path = (
                    output_dir
                    / filename
                )

                export_clip(
                    source_audio=(
                        audio_path
                    ),
                    output_path=(
                        output_path
                    ),
                    start_sec=(
                        export_start
                    ),
                    end_sec=(
                        export_end
                    ),
                )

                record[
                    "audio_file"
                ] = str(
                    output_path
                )

                exported_for_question += 1

            manifest.append(
                record
            )

            status = (
                "EXPORT"
                if turn[
                    "export_for_asr"
                ]
                else "SKIP"
            )

            raw_start = float(
                turn["start_sec"]
            )

            raw_end = float(
                turn["end_sec"]
            )

            flags = []

            if bounds[
                "padding_clipped_for_speaker"
            ]:
                flags.append(
                    "PAD_CLIPPED"
                )

            if bounds[
                "raw_cross_speaker_overlap"
            ]:
                flags.append(
                    (
                        "RAW_OVERLAP="
                        f"{bounds['raw_cross_speaker_overlap_sec']:.3f}s"
                    )
                )

            flag_text = (
                " | ".join(
                    flags
                )
                if flags
                else "-"
            )

            print(
                f"  "
                f"{turn['turn_index']:02d} "
                f"{turn['role']:10} "
                f"{raw_start:7.3f}"
                f" → "
                f"{raw_end:7.3f} "
                f"src="
                f"{turn['source_segment_indices']} "
                f"{status:6} "
                f"export="
                f"{export_start:.3f}"
                f"→"
                f"{export_end:.3f} "
                f"{flag_text}"
            )

        print(
            f"  exported: "
            f"{exported_for_question}"
        )

        print()

    manifest_path = (
        sample_dir
        / args.manifest_name
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    exported_count = sum(
        bool(
            item["audio_file"]
        )
        for item in manifest
    )

    skipped_count = (
        len(manifest)
        - exported_count
    )

    overlap_count = sum(
        bool(
            item[
                "raw_cross_speaker_overlap"
            ]
        )
        for item in manifest
    )

    clipped_count = sum(
        bool(
            item[
                "padding_clipped_for_speaker"
            ]
        )
        for item in manifest
    )

    print(
        "=== EXPORT COMPLETE ==="
    )

    print()

    print(
        f"Turn records:       "
        f"{len(manifest)}"
    )

    print(
        f"ASR clips:          "
        f"{exported_count}"
    )

    print(
        f"Skipped tiny:       "
        f"{skipped_count}"
    )

    print(
        f"Raw overlaps:       "
        f"{overlap_count}"
    )

    print(
        f"Padding clipped:    "
        f"{clipped_count}"
    )

    print()

    print(
        f"Audio:    "
        f"{output_dir}"
    )

    print(
        f"Manifest: "
        f"{manifest_path}"
    )


if __name__ == "__main__":
    main()