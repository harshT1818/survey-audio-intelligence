import argparse
import json
import subprocess
from pathlib import Path

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
        / "prompting_turn_audio"
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

        print(
            f"{tag}"
        )

        exported_for_question = 0

        for turn in turns:
            raw_start = float(
                turn["start_sec"]
            )

            raw_end = float(
                turn["end_sec"]
            )

            padded_start = max(
                0.0,
                raw_start
                - args.padding_sec,
            )

            padded_end = (
                raw_end
                + args.padding_sec
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
                "padded_start_sec": (
                    round(
                        padded_start,
                        3,
                    )
                ),
                "padded_end_sec": (
                    round(
                        padded_end,
                        3,
                    )
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
                        padded_start
                    ),
                    end_sec=(
                        padded_end
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

            print(
                f"  "
                f"{turn['turn_index']:02d} "
                f"{turn['role']:10} "
                f"{raw_start:7.2f}"
                f" → "
                f"{raw_end:7.2f} "
                f"{turn['duration_sec']:5.2f}s "
                f"{status}"
            )

        print(
            f"  exported: "
            f"{exported_for_question}"
        )

        print()

    manifest_path = (
        sample_dir
        / "prompting_turn_manifest.json"
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

    print(
        "=== EXPORT COMPLETE ==="
    )
    print()

    print(
        f"Turn records: "
        f"{len(manifest)}"
    )

    print(
        f"ASR clips:    "
        f"{exported_count}"
    )

    print(
        f"Skipped tiny: "
        f"{skipped_count}"
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