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
        / "prompting_turn_manifest_clean.json"
    )

    asr_path = (
        sample_dir
        / "prompting_turn_asr_results_clean.json"
    )

    output_path = (
        sample_dir
        / "prompting_dialogue_clean.json"
    )

    manifest = load_json(
        manifest_path
    )

    asr_results = load_json(
        asr_path
    )

    if not isinstance(
        manifest,
        list,
    ):
        raise ValueError(
            "Clean prompting manifest "
            "must be a JSON list."
        )

    if not isinstance(
        asr_results,
        list,
    ):
        raise ValueError(
            "Clean ASR results "
            "must be a JSON list."
        )

    dialogues = (
        build_prompting_dialogue(
            manifest=manifest,
            asr_results=asr_results,
        )
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
        "=== CLEAN PROMPTING DIALOGUE ==="
    )
    print()

    print(
        f"Response ID: "
        f"{args.response_id}"
    )

    print(
        f"Manifest rows: "
        f"{len(manifest)}"
    )

    print(
        f"ASR rows:      "
        f"{len(asr_results)}"
    )

    print(
        f"Questions:     "
        f"{len(dialogues)}"
    )

    print()

    wanted = {
        "state_govt_change_party",
        "mla_choice",
        "cm_choice",
    }

    for dialogue in dialogues:
        tag = dialogue.get(
            "tag"
        )

        if tag not in wanted:
            continue

        print(
            "=" * 90
        )

        print(tag)

        print(
            f"Evidence: "
            f"{dialogue.get('evidence_status')}"
        )

        print()

        for turn in dialogue.get(
            "turns",
            [],
        ):
            if (
                turn.get(
                    "asr_status"
                )
                != "COMPLETE"
            ):
                continue

            transcript = str(
                turn.get(
                    "transcript",
                    "",
                )
            ).strip()

            if not transcript:
                continue

            overlap = (
                " RAW_OVERLAP"
                if turn.get(
                    "raw_cross_speaker_overlap"
                )
                else ""
            )

            print(
                f"  "
                f"{float(turn['start_sec']):7.3f}"
                f"-"
                f"{float(turn['end_sec']):7.3f} "
                f"{str(turn.get('role')):10}"
                f"{overlap}"
            )

            print(
                f"    {transcript}"
            )

        print()

    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()