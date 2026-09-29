from pathlib import Path
from typing import Any


def normalize_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value).split()
    )


def basename(
    value: str | None,
) -> str | None:
    if not value:
        return None

    return Path(value).name


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


def build_asr_lookup(
    asr_results: list[
        dict[str, Any]
    ],
) -> dict[str, str]:
    result = {}

    for row in asr_results:
        filename = basename(
            row.get(
                "audio_file"
            )
        )

        if not filename:
            continue

        result[filename] = (
            normalize_text(
                row.get(
                    "transcript",
                    "",
                )
            )
        )

    return result


def build_prompting_dialogue(
    manifest: list[
        dict[str, Any]
    ],
    asr_results: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:
    asr_lookup = build_asr_lookup(
        asr_results
    )

    by_tag: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for row in manifest:
        tag = str(
            row.get(
                "tag",
                "",
            )
        )

        if not tag:
            continue

        by_tag.setdefault(
            tag,
            [],
        ).append(
            row
        )

    questions = []

    for tag, rows in by_tag.items():
        rows = sorted(
            rows,
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
                int(
                    item.get(
                        "turn_index",
                        0,
                    )
                ),
            ),
        )

        first = rows[0]

        turns = []

        previous = None

        for row in rows:
            audio_filename = basename(
                row.get(
                    "audio_file"
                )
            )

            exported = bool(
                row.get(
                    "export_for_asr"
                )
            )

            if not exported:
                transcript = ""

                asr_status = "SKIPPED_SHORT"

            elif (
                audio_filename
                not in asr_lookup
            ):
                transcript = ""

                asr_status = "MISSING"

            else:
                transcript = (
                    asr_lookup[
                        audio_filename
                    ]
                )

                if transcript:
                    asr_status = "COMPLETE"
                else:
                    asr_status = "EMPTY"

            start_sec = float(
                row["start_sec"]
            )

            end_sec = float(
                row["end_sec"]
            )

            overlap_previous = 0.0

            cross_speaker_overlap = False

            if previous is not None:
                overlap_previous = (
                    interval_overlap_sec(
                        float(
                            previous[
                                "start_sec"
                            ]
                        ),
                        float(
                            previous[
                                "end_sec"
                            ]
                        ),
                        start_sec,
                        end_sec,
                    )
                )

                cross_speaker_overlap = (
                    overlap_previous > 0
                    and (
                        previous.get(
                            "speaker_id"
                        )
                        != row.get(
                            "speaker_id"
                        )
                    )
                )

            turn = {
                "turn_index": (
                    row.get(
                        "turn_index"
                    )
                ),
                "speaker_id": (
                    row.get(
                        "speaker_id"
                    )
                ),
                "role": row.get(
                    "role",
                    "unknown",
                ),
                "role_confidence": (
                    row.get(
                        "role_confidence"
                    )
                ),
                "start_sec": round(
                    start_sec,
                    3,
                ),
                "end_sec": round(
                    end_sec,
                    3,
                ),
                "duration_sec": round(
                    end_sec
                    - start_sec,
                    3,
                ),
                "touches_core": bool(
                    row.get(
                        "touches_core",
                        False,
                    )
                ),
                "regions": row.get(
                    "regions",
                    [],
                ),
                "export_for_asr": (
                    exported
                ),
                "audio_file": (
                    audio_filename
                ),
                "asr_status": (
                    asr_status
                ),
                "transcript": (
                    transcript
                ),
                "overlap_with_previous_sec": (
                    overlap_previous
                ),
                "cross_speaker_overlap": (
                    cross_speaker_overlap
                ),
            }

            turns.append(
                turn
            )

            previous = row

        agent_turns = [
            turn
            for turn in turns
            if turn["role"]
            == "agent"
        ]

        respondent_turns = [
            turn
            for turn in turns
            if turn["role"]
            == "respondent"
        ]

        usable_agent_turns = [
            turn
            for turn in agent_turns
            if turn["transcript"]
        ]

        usable_respondent_turns = [
            turn
            for turn in respondent_turns
            if turn["transcript"]
        ]

        missing_asr_count = sum(
            turn["asr_status"]
            == "MISSING"
            for turn in turns
        )

        empty_asr_count = sum(
            turn["asr_status"]
            == "EMPTY"
            for turn in turns
        )

        skipped_count = sum(
            turn["asr_status"]
            == "SKIPPED_SHORT"
            for turn in turns
        )

        overlap_count = sum(
            turn[
                "cross_speaker_overlap"
            ]
            for turn in turns
        )

        if (
            usable_agent_turns
            and usable_respondent_turns
        ):
            evidence_status = (
                "ROLE_DIALOGUE_AVAILABLE"
            )

        elif usable_agent_turns:
            evidence_status = (
                "AGENT_ONLY_ASR"
            )

        elif usable_respondent_turns:
            evidence_status = (
                "RESPONDENT_ONLY_ASR"
            )

        else:
            evidence_status = (
                "NO_ROLE_DIALOGUE"
            )

        questions.append(
            {
                "question_index": (
                    first.get(
                        "question_index"
                    )
                ),
                "tag": tag,
                "question_text": (
                    first.get(
                        "question_text"
                    )
                ),
                "stored_response": (
                    first.get(
                        "stored_response"
                    )
                ),
                "evidence_status": (
                    evidence_status
                ),
                "turn_count": len(
                    turns
                ),
                "agent_turn_count": len(
                    agent_turns
                ),
                "respondent_turn_count": (
                    len(
                        respondent_turns
                    )
                ),
                "usable_agent_turn_count": (
                    len(
                        usable_agent_turns
                    )
                ),
                "usable_respondent_turn_count": (
                    len(
                        usable_respondent_turns
                    )
                ),
                "skipped_short_count": (
                    skipped_count
                ),
                "missing_asr_count": (
                    missing_asr_count
                ),
                "empty_asr_count": (
                    empty_asr_count
                ),
                "cross_speaker_overlap_count": (
                    overlap_count
                ),
                "turns": turns,
            }
        )

    questions.sort(
        key=lambda item: int(
            item.get(
                "question_index",
                999999,
            )
        )
    )

    return questions