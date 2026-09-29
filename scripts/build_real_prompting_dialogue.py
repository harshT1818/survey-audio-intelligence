import argparse
import json
from pathlib import Path

from src.full_sample.prompting_dialogue import (
    build_prompting_dialogue,
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


def shorten(
    text: str,
    maximum: int = 120,
) -> str:
    text = " ".join(
        text.split()
    )

    if len(text) <= maximum:
        return text

    return (
        text[:maximum - 3]
        + "..."
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

    manifest_path = (
        sample_dir
        / "prompting_turn_manifest.json"
    )

    asr_path = (
        sample_dir
        / "prompting_turn_asr_results.json"
    )

    manifest = load_json(
        manifest_path
    )

    asr_results = load_json(
        asr_path
    )

    dialogues = (
        build_prompting_dialogue(
            manifest=manifest,
            asr_results=asr_results,
        )
    )

    output_path = (
        sample_dir
        / "prompting_dialogue.json"
    )

    output_path.write_text(
        json.dumps(
            dialogues,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "=== REAL PROMPTING "
        "DIALOGUE ==="
    )
    print()

    print(
        f"Response ID: "
        f"{args.response_id}"
    )

    print(
        f"Questions:   "
        f"{len(dialogues)}"
    )

    print()

    for question in dialogues:
        print(
            "=" * 100
        )

        print(
            f"["
            f"{question['question_index']:02d}"
            f"] "
            f"{question['tag']}"
        )

        print(
            f"Stored answer: "
            f"{question['stored_response']}"
        )

        print(
            f"Evidence:      "
            f"{question['evidence_status']}"
        )

        print(
            f"Turns:         "
            f"{question['turn_count']} "
            f"| agent "
            f"{question['agent_turn_count']} "
            f"| respondent "
            f"{question['respondent_turn_count']}"
        )

        print(
            f"ASR usable:    "
            f"agent "
            f"{question['usable_agent_turn_count']} "
            f"| respondent "
            f"{question['usable_respondent_turn_count']}"
        )

        print(
            f"Skipped tiny:  "
            f"{question['skipped_short_count']}"
        )

        print(
            f"Cross overlaps:"
            f" "
            f"{question['cross_speaker_overlap_count']}"
        )

        print()

        for turn in question[
            "turns"
        ]:
            role = str(
                turn["role"]
            ).upper()

            flags = []

            if (
                turn["asr_status"]
                != "COMPLETE"
            ):
                flags.append(
                    turn["asr_status"]
                )

            if turn[
                "cross_speaker_overlap"
            ]:
                flags.append(
                    "OVERLAP"
                )

            flag_text = (
                f" [{' | '.join(flags)}]"
                if flags
                else ""
            )

            print(
                f"{turn['start_sec']:7.2f}"
                f"–"
                f"{turn['end_sec']:7.2f} "
                f"{role:10}"
                f"{flag_text}"
            )

            if turn[
                "transcript"
            ]:
                print(
                    "    "
                    + shorten(
                        turn[
                            "transcript"
                        ]
                    )
                )

        print()

    print(
        "=" * 100
    )

    print()

    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()