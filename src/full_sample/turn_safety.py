from typing import Any


def decision_rejection_reasons(
    turn: dict[str, Any],
) -> list[str]:
    reasons = []

    if (
        turn.get(
            "asr_status"
        )
        != "COMPLETE"
    ):
        reasons.append(
            "ASR_NOT_COMPLETE"
        )

    if not str(
        turn.get(
            "transcript",
            "",
        )
    ).strip():
        reasons.append(
            "EMPTY_TRANSCRIPT"
        )

    if (
        turn.get(
            "role"
        )
        in {
            None,
            "",
            "unknown",
        }
    ):
        reasons.append(
            "UNKNOWN_ROLE"
        )

    if bool(
        turn.get(
            "raw_cross_speaker_overlap",
            False,
        )
    ):
        reasons.append(
            "RAW_CROSS_SPEAKER_OVERLAP"
        )

    if float(
        turn.get(
            "raw_cross_speaker_overlap_sec",
            0.0,
        )
        or 0.0
    ) > 0:
        reasons.append(
            "RAW_CROSS_SPEAKER_OVERLAP"
        )

    if bool(
        turn.get(
            "cross_speaker_overlap",
            False,
        )
    ):
        reasons.append(
            "CROSS_SPEAKER_OVERLAP"
        )

    return list(
        dict.fromkeys(
            reasons
        )
    )


def is_decision_safe(
    turn: dict[str, Any],
) -> bool:
    return not (
        decision_rejection_reasons(
            turn
        )
    )


def turns_after(
    turns: list[
        dict[str, Any]
    ],
    start_sec: float,
    role: str,
    tolerance_sec: float = 0.15,
) -> list[dict[str, Any]]:
    result = []

    for turn in turns:
        if (
            turn.get(
                "role"
            )
            != role
        ):
            continue

        if float(
            turn.get(
                "start_sec",
                0.0,
            )
        ) < (
            start_sec
            - tolerance_sec
        ):
            continue

        result.append(
            turn
        )

    result.sort(
        key=lambda item: (
            float(
                item.get(
                    "start_sec",
                    0.0,
                )
            ),
            float(
                item.get(
                    "end_sec",
                    0.0,
                )
            ),
        )
    )

    return result


def select_first_safe_turn_after(
    turns: list[
        dict[str, Any]
    ],
    start_sec: float,
    role: str,
    tolerance_sec: float = 0.15,
) -> dict[str, Any]:
    candidates = turns_after(
        turns=turns,
        start_sec=start_sec,
        role=role,
        tolerance_sec=(
            tolerance_sec
        ),
    )

    rejected = []

    for turn in candidates:
        reasons = (
            decision_rejection_reasons(
                turn
            )
        )

        if not reasons:
            return {
                "turn": turn,
                "rejected": (
                    rejected
                ),
            }

        rejected.append(
            {
                "turn": turn,
                "reasons": reasons,
            }
        )

    return {
        "turn": None,
        "rejected": rejected,
    }


def safe_turns_after(
    turns: list[
        dict[str, Any]
    ],
    start_sec: float,
    role: str,
    tolerance_sec: float = 0.15,
) -> dict[str, Any]:
    candidates = turns_after(
        turns=turns,
        start_sec=start_sec,
        role=role,
        tolerance_sec=(
            tolerance_sec
        ),
    )

    accepted = []
    rejected = []

    for turn in candidates:
        reasons = (
            decision_rejection_reasons(
                turn
            )
        )

        if reasons:
            rejected.append(
                {
                    "turn": turn,
                    "reasons": reasons,
                }
            )
        else:
            accepted.append(
                turn
            )

    return {
        "accepted": accepted,
        "rejected": rejected,
    }