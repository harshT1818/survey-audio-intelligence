import argparse
import json
from pathlib import Path

from src.full_sample.dialogue_segments import (
    build_question_dialogue_segments,
)


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


def main():
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--response-id",
        required=True,
    )

    parser.add_argument(
        "--context-before-sec",
        type=float,
        default=1.5,
    )

    parser.add_argument(
        "--context-after-sec",
        type=float,
        default=1.5,
    )

    args = parser.parse_args()

    sample_dir = (
        Path("data/private/r2")
        / args.response_id
    )

    question_asr_path = (
        sample_dir
        / "question_asr.json"
    )

    diarization_path = (
        sample_dir
        / (
            "interview_16k_mono_"
            "diarization.json"
        )
    )

    questions = load_json(
        question_asr_path
    )

    diarization = load_json(
        diarization_path
    )

    results = (
        build_question_dialogue_segments(
            questions=questions,
            diarization_payload=(
                diarization
            ),
            context_before_sec=(
                args.context_before_sec
            ),
            context_after_sec=(
                args.context_after_sec
            ),
        )
    )

    output_path = (
        sample_dir
        / (
            "question_dialogue_"
            "segments.json"
        )
    )

    output_path.write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "=== QUESTION DIALOGUE "
        "SEGMENTS ==="
    )
    print()

    print(
        f"Response ID: "
        f"{args.response_id}"
    )

    print(
        f"Questions:   "
        f"{len(results)}"
    )

    print(
        f"Context:     "
        f"-{args.context_before_sec:.1f}s "
        f"/ +{args.context_after_sec:.1f}s"
    )

    print()

    one_speaker = 0
    two_plus = 0
    zero_speaker = 0

    for question in results:
        count = question[
            "speaker_count_in_core"
        ]

        if count == 0:
            zero_speaker += 1

        elif count == 1:
            one_speaker += 1

        else:
            two_plus += 1

        stats = (
            question[
                "speaker_stats"
            ]
        )

        summary = ", ".join(
            (
                f"{stat['speaker_id']}: "
                f"{stat['core_speech_sec']:.2f}s"
            )
            for stat in stats
        )

        if not summary:
            summary = "no speech"

        print(
            f"["
            f"{question['question_index']:02d}"
            f"] "
            f"{question['tag']:35} "
            f"speakers={count} "
            f"| {summary}"
        )

    print()
    print(
        "=== SUMMARY ==="
    )
    print()

    print(
        f"No speaker in core: "
        f"{zero_speaker}"
    )

    print(
        f"One speaker:        "
        f"{one_speaker}"
    )

    print(
        f"Two+ speakers:      "
        f"{two_plus}"
    )

    print()
    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()