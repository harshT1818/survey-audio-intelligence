from pathlib import Path
from typing import Any


def normalize_text(
    text: str,
) -> str:
    return " ".join(
        str(text).split()
    )


def merge_text_parts(
    parts: list[str],
    maximum_overlap_tokens: int = 15,
) -> str:
    """
    Merge overlapping ASR chunks.

    The audio chunks overlap by a few seconds, so the same
    words can occur at the end of one transcript and the
    start of the next transcript.

    Only exact token overlaps are removed here. We avoid
    aggressive fuzzy cleanup because raw ASR evidence must
    remain conservative.
    """
    cleaned = [
        normalize_text(part)
        for part in parts
        if normalize_text(part)
    ]

    if not cleaned:
        return ""

    merged_tokens = (
        cleaned[0].split()
    )

    for part in cleaned[1:]:
        next_tokens = part.split()

        maximum = min(
            maximum_overlap_tokens,
            len(merged_tokens),
            len(next_tokens),
        )

        overlap_size = 0

        for size in range(
            maximum,
            0,
            -1,
        ):
            if (
                merged_tokens[-size:]
                == next_tokens[:size]
            ):
                overlap_size = size
                break

        merged_tokens.extend(
            next_tokens[
                overlap_size:
            ]
        )

    return " ".join(
        merged_tokens
    )


def _basename(
    value: str,
) -> str:
    return Path(
        value
    ).name


def _question_gaps(
    questions: list[
        dict[str, Any]
    ],
    index: int,
) -> tuple[
    float | None,
    float | None,
]:
    current = questions[index]

    gap_before = None
    gap_after = None

    if index > 0:
        previous = (
            questions[index - 1]
        )

        gap_before = round(
            float(
                current["start_sec"]
            )
            - float(
                previous["end_sec"]
            ),
            3,
        )

    if (
        index + 1
        < len(questions)
    ):
        following = (
            questions[index + 1]
        )

        gap_after = round(
            float(
                following["start_sec"]
            )
            - float(
                current["end_sec"]
            ),
            3,
        )

    return (
        gap_before,
        gap_after,
    )


def build_question_asr_records(
    questions: list[
        dict[str, Any]
    ],
    batch_manifest: list[
        dict[str, Any]
    ],
    asr_results: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    transcript_by_file = {
        _basename(
            row["audio_file"]
        ): normalize_text(
            row.get(
                "transcript",
                "",
            )
        )
        for row
        in asr_results
    }

    chunks_by_question: dict[
        int,
        list[dict[str, Any]],
    ] = {}

    for chunk in batch_manifest:
        question_index = int(
            chunk[
                "question_index"
            ]
        )

        chunks_by_question.setdefault(
            question_index,
            [],
        ).append(
            chunk
        )

    records = []

    for (
        question_position,
        question,
    ) in enumerate(
        questions
    ):
        question_index = int(
            question["index"]
        )

        chunks = sorted(
            chunks_by_question.get(
                question_index,
                [],
            ),
            key=lambda item: int(
                item[
                    "chunk_index"
                ]
            ),
        )

        chunk_records = []

        transcripts = []

        missing_files = []

        empty_files = []

        for chunk in chunks:
            filename = _basename(
                chunk[
                    "audio_file"
                ]
            )

            if (
                filename
                not in transcript_by_file
            ):
                transcript = ""

                missing_files.append(
                    filename
                )
            else:
                transcript = (
                    transcript_by_file[
                        filename
                    ]
                )

                if not transcript:
                    empty_files.append(
                        filename
                    )

            transcripts.append(
                transcript
            )

            chunk_records.append(
                {
                    "chunk_index": (
                        chunk[
                            "chunk_index"
                        ]
                    ),
                    "audio_file": (
                        filename
                    ),
                    "absolute_start_sec": (
                        chunk[
                            "absolute_start_sec"
                        ]
                    ),
                    "absolute_end_sec": (
                        chunk[
                            "absolute_end_sec"
                        ]
                    ),
                    "transcript": (
                        transcript
                    ),
                }
            )

        merged_transcript = (
            merge_text_parts(
                transcripts
            )
        )

        if not merged_transcript:
            asr_status = "EMPTY"

        elif (
            missing_files
            or empty_files
        ):
            asr_status = "PARTIAL"

        else:
            asr_status = "COMPLETE"

        (
            gap_before,
            gap_after,
        ) = _question_gaps(
            questions=questions,
            index=question_position,
        )

        duration_sec = float(
            question[
                "duration_sec"
            ]
        )

        overlap_review_required = any(
            bool(
                chunk.get(
                    "overlap_review_required"
                )
            )
            for chunk in chunks
        )

        very_short_window = (
            duration_sec < 2.0
        )

        tight_before = (
            gap_before is not None
            and gap_before < 2.0
        )

        tight_after = (
            gap_after is not None
            and gap_after < 2.0
        )

        boundary_context_needed = (
            very_short_window
            or tight_before
            or tight_after
            or overlap_review_required
        )

        records.append(
            {
                "question_index": (
                    question_index
                ),
                "tag": question.get(
                    "tag"
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
                "english_value": (
                    question.get(
                        "english_value"
                    )
                ),
                "hindi_value": (
                    question.get(
                        "hindi_value"
                    )
                ),
                "start_sec": (
                    question[
                        "start_sec"
                    ]
                ),
                "end_sec": (
                    question[
                        "end_sec"
                    ]
                ),
                "duration_sec": (
                    duration_sec
                ),
                "gap_before_sec": (
                    gap_before
                ),
                "gap_after_sec": (
                    gap_after
                ),
                "chunk_count": (
                    len(chunks)
                ),
                "asr_status": (
                    asr_status
                ),
                "missing_chunk_files": (
                    missing_files
                ),
                "empty_chunk_files": (
                    empty_files
                ),
                "overlap_review_required": (
                    overlap_review_required
                ),
                "very_short_window": (
                    very_short_window
                ),
                "boundary_context_needed": (
                    boundary_context_needed
                ),
                "chunks": (
                    chunk_records
                ),
                "transcript": (
                    merged_transcript
                ),
            }
        )

    return records