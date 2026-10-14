import argparse
import json
from pathlib import Path

from src.full_sample.asr_batch import (
    export_audio_chunk,
    find_question_overlaps,
    split_duration,
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--response-id",
        required=True,
    )

    parser.add_argument(
        "--max-chunk-sec",
        type=float,
        default=20.0,
    )

    parser.add_argument(
        "--overlap-sec",
        type=float,
        default=2.0,
    )

    args = parser.parse_args()

    sample_dir = (
        Path(
            "data/private/r2"
        )
        / args.response_id
    )

    question_manifest_path = (
        sample_dir
        / "question_audio_manifest.json"
    )

    if not question_manifest_path.exists():
        raise FileNotFoundError(
            f"Missing: "
            f"{question_manifest_path}"
        )

    questions = json.loads(
        question_manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        questions,
        list,
    ):
        raise ValueError(
            "Question audio manifest "
            "must be a JSON list."
        )

    output_dir = (
        sample_dir
        / "question_asr_chunks"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_manifest_path = (
        sample_dir
        / "question_asr_batch_manifest.json"
    )

    overlap_report_path = (
        sample_dir
        / "question_overlap_report.json"
    )

    overlaps = (
        find_question_overlaps(
            questions
        )
    )

    batch = []

    print()
    print(
        "=== PREPARING REAL "
        "QUESTION ASR BATCH ==="
    )
    print()

    print(
        f"Response ID: "
        f"{args.response_id}"
    )

    print(
        f"Questions:   "
        f"{len(questions)}"
    )

    print(
        f"Chunk size:  "
        f"{args.max_chunk_sec:.1f}s"
    )

    print(
        f"Overlap:     "
        f"{args.overlap_sec:.1f}s"
    )

    print()

    total_chunks = 0

    for question in questions:
        index = int(
            question["index"]
        )

        tag = str(
            question["tag"]
        )

        question_audio = Path(
            question["audio_file"]
        )

        duration_sec = float(
            question["duration_sec"]
        )

        intervals = split_duration(
            duration_sec=duration_sec,
            max_chunk_sec=(
                args.max_chunk_sec
            ),
            overlap_sec=(
                args.overlap_sec
            ),
        )

        question_overlap_info = (
            overlaps.get(
                tag,
                [],
            )
        )

        print(
            f"{index:03d} "
            f"{tag:35} "
            f"{duration_sec:6.2f}s "
            f"→ "
            f"{len(intervals)} chunk(s)"
        )

        if question_overlap_info:
            for overlap in (
                question_overlap_info
            ):
                print(
                    "    WARNING: overlaps "
                    f"{overlap['tag']} by "
                    f"{overlap['overlap_sec']:.3f}s"
                )

        for (
            chunk_index,
            (
                local_start,
                local_end,
            ),
        ) in enumerate(
            intervals,
            start=1,
        ):
            filename = (
                f"{index:03d}_"
                f"{tag}_"
                f"chunk_"
                f"{chunk_index:02d}.wav"
            )

            output_path = (
                output_dir
                / filename
            )

            export_audio_chunk(
                source_audio=(
                    question_audio
                ),
                output_path=(
                    output_path
                ),
                start_sec=(
                    local_start
                ),
                end_sec=(
                    local_end
                ),
            )

            absolute_start = round(
                float(
                    question[
                        "start_sec"
                    ]
                )
                + local_start,
                3,
            )

            absolute_end = round(
                float(
                    question[
                        "start_sec"
                    ]
                )
                + local_end,
                3,
            )

            batch.append(
                {
                    "response_id": (
                        args.response_id
                    ),
                    "question_index": (
                        index
                    ),
                    "tag": tag,
                    "chunk_index": (
                        chunk_index
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
                    "local_start_sec": (
                        local_start
                    ),
                    "local_end_sec": (
                        local_end
                    ),
                    "absolute_start_sec": (
                        absolute_start
                    ),
                    "absolute_end_sec": (
                        absolute_end
                    ),
                    "duration_sec": round(
                        local_end
                        - local_start,
                        3,
                    ),
                    "audio_file": str(
                        output_path
                    ),
                    "question_overlaps": (
                        question_overlap_info
                    ),
                    "overlap_review_required": (
                        bool(
                            question_overlap_info
                        )
                    ),
                }
            )

            total_chunks += 1

    output_manifest_path.write_text(
        json.dumps(
            batch,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    overlap_report = {
        tag: values
        for tag, values
        in overlaps.items()
        if values
    }

    overlap_report_path.write_text(
        json.dumps(
            overlap_report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "=== ASR BATCH READY ==="
    )
    print()

    print(
        f"Questions:       "
        f"{len(questions)}"
    )

    print(
        f"ASR chunks:      "
        f"{total_chunks}"
    )

    print(
        f"Overlap-risk "
        f"questions: "
        f"{len(overlap_report)}"
    )

    print()

    print(
        f"Chunks:   "
        f"{output_dir}"
    )

    print(
        f"Manifest: "
        f"{output_manifest_path}"
    )

    print(
        f"Overlap:  "
        f"{overlap_report_path}"
    )


if __name__ == "__main__":
    main()