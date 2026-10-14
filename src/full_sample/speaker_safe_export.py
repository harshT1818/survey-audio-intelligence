from typing import Any


def interval_overlap_sec(
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


def speaker_safe_export_bounds(
    turn: dict[str, Any],
    all_turns: list[
        dict[str, Any]
    ],
    padding_sec: float,
) -> dict[str, Any]:
    """
    Add ASR context padding without allowing the added
    padding to enter another speaker's raw interval.

    Important:
    If the raw diarization intervals themselves overlap,
    we do NOT silently trim the raw turn.

    Instead we:
        - preserve the raw diarization interval
        - mark the raw cross-speaker overlap
        - prevent additional padding contamination

    This keeps the diarization evidence auditable.
    """
    if padding_sec < 0:
        raise ValueError(
            "padding_sec cannot be negative."
        )

    raw_start = float(
        turn["start_sec"]
    )

    raw_end = float(
        turn["end_sec"]
    )

    if raw_end <= raw_start:
        raise ValueError(
            "Turn end must be after "
            "turn start."
        )

    speaker_id = str(
        turn["speaker_id"]
    )

    desired_start = max(
        0.0,
        raw_start - padding_sec,
    )

    desired_end = (
        raw_end + padding_sec
    )

    safe_start = desired_start
    safe_end = desired_end

    raw_overlaps = []

    for other in all_turns:
        if other is turn:
            continue

        other_speaker = str(
            other.get(
                "speaker_id"
            )
        )

        if (
            other_speaker
            == speaker_id
        ):
            continue

        other_start = float(
            other["start_sec"]
        )

        other_end = float(
            other["end_sec"]
        )

        raw_overlap = (
            interval_overlap_sec(
                raw_start,
                raw_end,
                other_start,
                other_end,
            )
        )

        if raw_overlap > 0:
            raw_overlaps.append(
                {
                    "turn_index": (
                        other.get(
                            "turn_index"
                        )
                    ),
                    "speaker_id": (
                        other_speaker
                    ),
                    "role": (
                        other.get(
                            "role"
                        )
                    ),
                    "start_sec": (
                        other_start
                    ),
                    "end_sec": (
                        other_end
                    ),
                    "overlap_sec": (
                        raw_overlap
                    ),
                }
            )

            # Another speaker is already active
            # across our raw left boundary.
            # Do not add extra left padding there.
            if (
                other_start
                < raw_start
                < other_end
            ):
                safe_start = max(
                    safe_start,
                    raw_start,
                )

            # Same protection on the right boundary.
            if (
                other_start
                < raw_end
                < other_end
            ):
                safe_end = min(
                    safe_end,
                    raw_end,
                )

        # Previous other-speaker speech:
        # don't pad backwards through it.
        if (
            other_end
            <= raw_start
            and other_end
            > safe_start
        ):
            safe_start = (
                other_end
            )

        # Following other-speaker speech:
        # don't pad forwards through it.
        if (
            other_start
            >= raw_end
            and other_start
            < safe_end
        ):
            safe_end = (
                other_start
            )

    # If raw overlap exists at all, be conservative:
    # added context should not expand the mixed region.
    if raw_overlaps:
        safe_start = max(
            safe_start,
            raw_start,
        )

        safe_end = min(
            safe_end,
            raw_end,
        )

    actual_left_padding = (
        raw_start - safe_start
    )

    actual_right_padding = (
        safe_end - raw_end
    )

    padding_clipped = (
        actual_left_padding
        < padding_sec - 0.0005
        or actual_right_padding
        < padding_sec - 0.0005
    )

    return {
        "raw_start_sec": round(
            raw_start,
            3,
        ),
        "raw_end_sec": round(
            raw_end,
            3,
        ),
        "export_start_sec": round(
            safe_start,
            3,
        ),
        "export_end_sec": round(
            safe_end,
            3,
        ),
        "requested_padding_sec": round(
            padding_sec,
            3,
        ),
        "actual_left_padding_sec": round(
            max(
                0.0,
                actual_left_padding,
            ),
            3,
        ),
        "actual_right_padding_sec": round(
            max(
                0.0,
                actual_right_padding,
            ),
            3,
        ),
        "padding_clipped_for_speaker": (
            padding_clipped
        ),
        "raw_cross_speaker_overlap": bool(
            raw_overlaps
        ),
        "raw_cross_speaker_overlap_sec": (
            round(
                max(
                    (
                        item[
                            "overlap_sec"
                        ]
                        for item
                        in raw_overlaps
                    ),
                    default=0.0,
                ),
                3,
            )
        ),
        "raw_overlapping_turns": (
            raw_overlaps
        ),
    }