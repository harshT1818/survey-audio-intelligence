from collections import defaultdict
from typing import Any


def overlap_sec(
    start_a: float,
    end_a: float,
    start_b: float,
    end_b: float,
) -> float:
    start = max(
        start_a,
        start_b,
    )

    end = min(
        end_a,
        end_b,
    )

    return round(
        max(
            0.0,
            end - start,
        ),
        3,
    )


def clip_interval(
    start_sec: float,
    end_sec: float,
    clip_start_sec: float,
    clip_end_sec: float,
) -> tuple[
    float,
    float,
] | None:
    start = max(
        start_sec,
        clip_start_sec,
    )

    end = min(
        end_sec,
        clip_end_sec,
    )

    if end <= start:
        return None

    return (
        round(
            start,
            3,
        ),
        round(
            end,
            3,
        ),
    )


def normalize_diarization_segments(
    diarization_payload: Any,
) -> list[dict[str, Any]]:
    if isinstance(
        diarization_payload,
        dict,
    ):
        raw_segments = (
            diarization_payload.get(
                "segments",
                [],
            )
        )

    elif isinstance(
        diarization_payload,
        list,
    ):
        raw_segments = (
            diarization_payload
        )

    else:
        raise ValueError(
            "Unexpected diarization JSON."
        )

    segments = []

    for index, raw in enumerate(
        raw_segments,
        start=1,
    ):
        if not isinstance(
            raw,
            dict,
        ):
            continue

        speaker_id = raw.get(
            "speaker_id"
        )

        start_sec = raw.get(
            "start_sec"
        )

        end_sec = raw.get(
            "end_sec"
        )

        if speaker_id is None:
            continue

        if not isinstance(
            start_sec,
            (int, float),
        ):
            continue

        if not isinstance(
            end_sec,
            (int, float),
        ):
            continue

        if end_sec <= start_sec:
            continue

        duration_sec = round(
            end_sec
            - start_sec,
            3,
        )

        segments.append(
            {
                "segment_index": index,
                "speaker_id": str(
                    speaker_id
                ),
                "start_sec": round(
                    float(start_sec),
                    3,
                ),
                "end_sec": round(
                    float(end_sec),
                    3,
                ),
                "duration_sec": (
                    duration_sec
                ),
                "micro_segment": (
                    duration_sec < 0.15
                ),
            }
        )

    segments.sort(
        key=lambda segment: (
            segment["start_sec"],
            segment["end_sec"],
        )
    )

    return segments


def intersect_question_with_speakers(
    question: dict[str, Any],
    diarization_segments: list[
        dict[str, Any]
    ],
    context_before_sec: float = 1.5,
    context_after_sec: float = 1.5,
) -> dict[str, Any]:
    question_start = float(
        question["start_sec"]
    )

    question_end = float(
        question["end_sec"]
    )

    evidence_start = max(
        0.0,
        question_start
        - context_before_sec,
    )

    evidence_end = (
        question_end
        + context_after_sec
    )

    evidence_segments = []

    speaker_stats: dict[
        str,
        dict[str, Any],
    ] = defaultdict(
        lambda: {
            "segment_count": 0,
            "core_segment_count": 0,
            "micro_segment_count": 0,
            "evidence_speech_sec": 0.0,
            "core_speech_sec": 0.0,
            "context_only_speech_sec": 0.0,
        }
    )

    for segment in diarization_segments:
        clipped = clip_interval(
            start_sec=segment[
                "start_sec"
            ],
            end_sec=segment[
                "end_sec"
            ],
            clip_start_sec=(
                evidence_start
            ),
            clip_end_sec=(
                evidence_end
            ),
        )

        if clipped is None:
            continue

        (
            clipped_start,
            clipped_end,
        ) = clipped

        evidence_overlap = round(
            clipped_end
            - clipped_start,
            3,
        )

        core_overlap = (
            overlap_sec(
                segment["start_sec"],
                segment["end_sec"],
                question_start,
                question_end,
            )
        )

        context_only_overlap = round(
            max(
                0.0,
                evidence_overlap
                - core_overlap,
            ),
            3,
        )

        touches_core = (
            core_overlap > 0
        )

        if (
            segment["end_sec"]
            <= question_start
        ):
            region = "context_before"

        elif (
            segment["start_sec"]
            >= question_end
        ):
            region = "context_after"

        elif touches_core:
            region = "core"

        else:
            region = "context"

        record = {
            "segment_index": (
                segment[
                    "segment_index"
                ]
            ),
            "speaker_id": (
                segment[
                    "speaker_id"
                ]
            ),
            "original_start_sec": (
                segment[
                    "start_sec"
                ]
            ),
            "original_end_sec": (
                segment[
                    "end_sec"
                ]
            ),
            "clipped_start_sec": (
                clipped_start
            ),
            "clipped_end_sec": (
                clipped_end
            ),
            "evidence_overlap_sec": (
                evidence_overlap
            ),
            "core_overlap_sec": (
                core_overlap
            ),
            "context_only_overlap_sec": (
                context_only_overlap
            ),
            "touches_core": (
                touches_core
            ),
            "region": region,
            "micro_segment": (
                segment[
                    "micro_segment"
                ]
            ),
        }

        evidence_segments.append(
            record
        )

        stats = speaker_stats[
            segment["speaker_id"]
        ]

        stats[
            "segment_count"
        ] += 1

        if touches_core:
            stats[
                "core_segment_count"
            ] += 1

        if segment[
            "micro_segment"
        ]:
            stats[
                "micro_segment_count"
            ] += 1

        stats[
            "evidence_speech_sec"
        ] = round(
            stats[
                "evidence_speech_sec"
            ]
            + evidence_overlap,
            3,
        )

        stats[
            "core_speech_sec"
        ] = round(
            stats[
                "core_speech_sec"
            ]
            + core_overlap,
            3,
        )

        stats[
            "context_only_speech_sec"
        ] = round(
            stats[
                "context_only_speech_sec"
            ]
            + context_only_overlap,
            3,
        )

    normalized_stats = []

    for (
        speaker_id,
        stats,
    ) in speaker_stats.items():
        normalized_stats.append(
            {
                "speaker_id": (
                    speaker_id
                ),
                **stats,
            }
        )

    normalized_stats.sort(
        key=lambda item: (
            -item[
                "core_speech_sec"
            ],
            -item[
                "evidence_speech_sec"
            ],
            item[
                "speaker_id"
            ],
        )
    )

    speakers_in_core = [
        stat["speaker_id"]
        for stat
        in normalized_stats
        if stat[
            "core_speech_sec"
        ] > 0
    ]

    return {
        "question_index": (
            question.get(
                "question_index",
                question.get(
                    "index"
                ),
            )
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
        "asr_status": (
            question.get(
                "asr_status"
            )
        ),
        "question_transcript": (
            question.get(
                "transcript",
                "",
            )
        ),
        "question_start_sec": (
            round(
                question_start,
                3,
            )
        ),
        "question_end_sec": (
            round(
                question_end,
                3,
            )
        ),
        "context_before_sec": (
            context_before_sec
        ),
        "context_after_sec": (
            context_after_sec
        ),
        "evidence_start_sec": (
            round(
                evidence_start,
                3,
            )
        ),
        "evidence_end_sec": (
            round(
                evidence_end,
                3,
            )
        ),
        "speaker_count_in_core": (
            len(
                speakers_in_core
            )
        ),
        "speakers_in_core": (
            speakers_in_core
        ),
        "speaker_stats": (
            normalized_stats
        ),
        "segments": (
            evidence_segments
        ),
    }


def build_question_dialogue_segments(
    questions: list[
        dict[str, Any]
    ],
    diarization_payload: Any,
    context_before_sec: float = 1.5,
    context_after_sec: float = 1.5,
) -> list[dict[str, Any]]:
    if context_before_sec < 0:
        raise ValueError(
            "context_before_sec "
            "cannot be negative."
        )

    if context_after_sec < 0:
        raise ValueError(
            "context_after_sec "
            "cannot be negative."
        )

    diarization_segments = (
        normalize_diarization_segments(
            diarization_payload
        )
    )

    results = []

    for question in questions:
        results.append(
            intersect_question_with_speakers(
                question=question,
                diarization_segments=(
                    diarization_segments
                ),
                context_before_sec=(
                    context_before_sec
                ),
                context_after_sec=(
                    context_after_sec
                ),
            )
        )

    return results