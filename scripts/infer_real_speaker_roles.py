import argparse
import json
from pathlib import Path

from src.full_sample.speaker_roles import (
    infer_speaker_roles,
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

    dialogue_path = (
        sample_dir
        / (
            "question_dialogue_"
            "segments.json"
        )
    )

    questions = load_json(
        dialogue_path
    )

    result = infer_speaker_roles(
        questions
    )

    output_path = (
        sample_dir
        / "speaker_roles.json"
    )

    output_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "=== SPEAKER ROLE "
        "INFERENCE ==="
    )
    print()

    print(
        f"Response ID: "
        f"{args.response_id}"
    )

    print(
        f"Status:      "
        f"{result['status']}"
    )

    if (
        result["status"]
        == "RESOLVED"
    ):
        print(
            f"Confidence:  "
            f"{result['confidence']}"
        )

        print()

        for (
            speaker_id,
            role_data,
        ) in result[
            "roles"
        ].items():
            print(
                f"{speaker_id:12} "
                f"→ "
                f"{role_data['role']:10} "
                f"("
                f"{role_data['confidence']}"
                f")"
            )

    else:
        print(
            f"Reason:      "
            f"{result['reason']}"
        )

    print()

    print(
        "Speaker totals:"
    )

    for (
        speaker_id,
        duration,
    ) in result[
        "speaker_totals_sec"
    ].items():
        print(
            f"  {speaker_id:12} "
            f"{duration:.2f}s"
        )

    print()

    print(
        "Evidence:"
    )

    for evidence in result[
        "evidence"
    ]:
        print(
            f"  - "
            f"{evidence['type']}: "
            f"{evidence}"
        )

    print()
    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()