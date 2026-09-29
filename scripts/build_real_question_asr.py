import argparse
import json
from pathlib import Path

from src.full_sample.question_asr import (
    build_question_asr_records,
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
    maximum: int = 110,
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

    questions = load_json(
        sample_dir
        / "question_audio_manifest.json"
    )

    batch = load_json(
        sample_dir
        / "question_asr_batch_manifest.json"
    )

    asr_results = load_json(
        sample_dir
        / "question_asr_chunk_results.json"
    )

    records = (
        build_question_asr_records(
            questions=questions,
            batch_manifest=batch,
            asr_results=asr_results,
        )
    )

    output_path = (
        sample_dir
        / "question_asr.json"
    )

    output_path.write_text(
        json.dumps(
            records,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "=== REAL QUESTION ASR ==="
    )
    print()

    print(
        f"Response ID: "
        f"{args.response_id}"
    )

    print(
        f"Questions:   "
        f"{len(records)}"
    )

    complete = sum(
        record["asr_status"]
        == "COMPLETE"
        for record in records
    )

    partial = sum(
        record["asr_status"]
        == "PARTIAL"
        for record in records
    )

    empty = sum(
        record["asr_status"]
        == "EMPTY"
        for record in records
    )

    boundary_risk = sum(
        record[
            "boundary_context_needed"
        ]
        for record in records
    )

    print(
        f"Complete ASR: "
        f"{complete}"
    )

    print(
        f"Partial ASR:  "
        f"{partial}"
    )

    print(
        f"Empty ASR:    "
        f"{empty}"
    )

    print(
        f"Boundary/context-risk: "
        f"{boundary_risk}"
    )

    print()
    print(
        "=" * 100
    )

    for record in records:
        flags = []

        if (
            record["asr_status"]
            != "COMPLETE"
        ):
            flags.append(
                record["asr_status"]
            )

        if record[
            "overlap_review_required"
        ]:
            flags.append(
                "OVERLAP"
            )

        if record[
            "very_short_window"
        ]:
            flags.append(
                "SHORT"
            )

        if record[
            "boundary_context_needed"
        ]:
            flags.append(
                "BOUNDARY"
            )

        flag_text = (
            ", ".join(flags)
            if flags
            else "OK"
        )

        print()
        print(
            f"[{record['question_index']:02d}] "
            f"{record['tag']}"
        )

        print(
            f"  Stored: "
            f"{record['stored_response']}"
        )

        print(
            f"  Flags:  "
            f"{flag_text}"
        )

        print(
            f"  ASR:    "
            f"{shorten(record['transcript'])}"
        )

    print()
    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()