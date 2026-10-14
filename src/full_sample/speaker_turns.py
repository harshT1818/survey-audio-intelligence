from typing import Any


def duration_sec(
    start_sec: float,
    end_sec: float,
) -> float:
    return round(
        max(
            0.0,
            end_sec - start_sec,
        ),
        3,
    )


def merge_same_speaker_segments(
    segments: list[dict[str, Any]],
    max_gap_sec: float = 0.60,
) -> list[dict[str, Any]]:
    """
    Merge nearby diarization fragments from the same speaker.

    We only merge when:
    - speaker is the same
    - chronological gap is small
    - there is no intervening different-speaker segment

    This is intentionally conservative.
    """
    if max_gap_sec < 0:
        raise ValueError(
            "max_gap_sec cannot be negative."
        )

    usable = []

    for segment in segments:
        start = float(
            segment[
                "clipped_start_sec"
            ]
        )

        end = float(
            segment[
                "clipped_end_sec"
            ]
        )

        if end <= start:
            continue

        usable.append(
            {
                "speaker_id": str(
                    segment[
                        "speaker_id"
                    ]
                ),
                "start_sec": start,
                "end_sec": end,
                "source_segment_indices": [
                    segment.get(
                        "segment_index"
                    )
                ],
                "regions": [
                    segment.get(
                        "region"
                    )
                ],
                "touches_core": bool(
                    segment.get(
                        "touches_core",
                        False,
                    )
                ),
            }
        )

    usable.sort(
        key=lambda item: (
            item["start_sec"],
            item["end_sec"],
        )
    )

    if not usable:
        return []

    merged = [
        usable[0]
    ]

    for current in usable[1:]:
        previous = merged[-1]

        gap = (
            current["start_sec"]
            - previous["end_sec"]
        )

        same_speaker = (
            current["speaker_id"]
            == previous["speaker_id"]
        )

        if (
            same_speaker
            and gap >= 0
            and gap <= max_gap_sec
        ):
            previous["end_sec"] = max(
                previous["end_sec"],
                current["end_sec"],
            )

            previous[
                "source_segment_indices"
            ].extend(
                current[
                    "source_segment_indices"
                ]
            )

            previous[
                "regions"
            ].extend(
                current["regions"]
            )

            previous["touches_core"] = (
                previous["touches_core"]
                or current[
                    "touches_core"
                ]
            )

        else:
            merged.append(
                current
            )

    for index, turn in enumerate(
        merged,
        start=1,
    ):
        turn["turn_index"] = index

        turn["duration_sec"] = (
            duration_sec(
                turn["start_sec"],
                turn["end_sec"],
            )
        )

    return merged


def add_role_to_turns(
    turns: list[dict[str, Any]],
    roles: dict[str, Any],
) -> list[dict[str, Any]]:
    output = []

    for turn in turns:
        speaker_id = turn[
            "speaker_id"
        ]

        role_data = roles.get(
            speaker_id,
            {},
        )

        output.append(
            {
                **turn,
                "role": role_data.get(
                    "role",
                    "unknown",
                ),
                "role_confidence": (
                    role_data.get(
                        "confidence"
                    )
                ),
            }
        )

    return output


def mark_turn_exportability(
    turns: list[dict[str, Any]],
    minimum_duration_sec: float = 0.35,
) -> list[dict[str, Any]]:
    """
    Very short diarization fragments are preserved in metadata
    but are not individually sent to ASR.
    """
    output = []

    for turn in turns:
        duration = float(
            turn[
                "duration_sec"
            ]
        )

        output.append(
            {
                **turn,
                "export_for_asr": (
                    duration
                    >= minimum_duration_sec
                ),
                "skip_reason": (
                    None
                    if duration
                    >= minimum_duration_sec
                    else (
                        "turn_too_short"
                    )
                ),
            }
        )

    return output