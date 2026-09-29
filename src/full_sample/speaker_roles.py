from collections import defaultdict
from typing import Any


def _speaker_core_time(
    question: dict[str, Any],
) -> dict[str, float]:
    result = {}

    for stat in question.get(
        "speaker_stats",
        [],
    ):
        speaker_id = stat.get(
            "speaker_id"
        )

        if not speaker_id:
            continue

        result[str(speaker_id)] = float(
            stat.get(
                "core_speech_sec",
                0.0,
            )
        )

    return result


def collect_speaker_totals(
    questions: list[
        dict[str, Any]
    ],
) -> dict[str, float]:
    totals: dict[
        str,
        float,
    ] = defaultdict(float)

    for question in questions:
        for (
            speaker_id,
            duration,
        ) in _speaker_core_time(
            question
        ).items():
            totals[
                speaker_id
            ] += duration

    return {
        speaker_id: round(
            duration,
            3,
        )
        for (
            speaker_id,
            duration,
        ) in totals.items()
    }


def find_question(
    questions: list[
        dict[str, Any]
    ],
    tag: str,
) -> dict[str, Any] | None:
    for question in questions:
        if question.get(
            "tag"
        ) == tag:
            return question

    return None


def infer_speaker_roles(
    questions: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    """
    Infer the global interviewer/respondent mapping.

    We intentionally use only strong structural evidence.

    The introduction is expected to be primarily interviewer
    speech, so a clearly dominant speaker there is the
    strongest role anchor.

    This does NOT claim that diarization assigned every
    individual turn correctly.
    """
    speaker_totals = (
        collect_speaker_totals(
            questions
        )
    )

    speakers = sorted(
        speaker_totals.keys()
    )

    if len(speakers) != 2:
        return {
            "status": "UNRESOLVED",
            "reason": (
                "Expected exactly two global "
                "diarization speakers."
            ),
            "speaker_totals_sec": (
                speaker_totals
            ),
            "roles": {},
            "evidence": [],
        }

    evidence = []

    introduction = find_question(
        questions,
        "introduction",
    )

    if introduction is None:
        return {
            "status": "UNRESOLVED",
            "reason": (
                "Introduction question "
                "was not available."
            ),
            "speaker_totals_sec": (
                speaker_totals
            ),
            "roles": {},
            "evidence": [],
        }

    intro_times = (
        _speaker_core_time(
            introduction
        )
    )

    if not intro_times:
        return {
            "status": "UNRESOLVED",
            "reason": (
                "No diarized speech found "
                "inside introduction."
            ),
            "speaker_totals_sec": (
                speaker_totals
            ),
            "roles": {},
            "evidence": [],
        }

    ranked_intro = sorted(
        intro_times.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    dominant_speaker = (
        ranked_intro[0][0]
    )

    dominant_duration = (
        ranked_intro[0][1]
    )

    other_duration = (
        ranked_intro[1][1]
        if len(ranked_intro) > 1
        else 0.0
    )

    evidence.append(
        {
            "type": (
                "introduction_anchor"
            ),
            "tag": "introduction",
            "speaker_id": (
                dominant_speaker
            ),
            "core_speech_sec": round(
                dominant_duration,
                3,
            ),
            "other_speaker_sec": round(
                other_duration,
                3,
            ),
            "interpretation": (
                "Introduction is expected "
                "to be interviewer-led."
            ),
        }
    )

    if dominant_duration < 2.0:
        return {
            "status": "UNRESOLVED",
            "reason": (
                "Introduction did not contain "
                "enough dominant speech."
            ),
            "speaker_totals_sec": (
                speaker_totals
            ),
            "roles": {},
            "evidence": evidence,
        }

    if (
        other_duration > 0
        and (
            dominant_duration
            / other_duration
        ) < 3.0
    ):
        return {
            "status": "UNRESOLVED",
            "reason": (
                "Introduction was not "
                "speaker-dominant enough."
            ),
            "speaker_totals_sec": (
                speaker_totals
            ),
            "roles": {},
            "evidence": evidence,
        }

    respondent_speaker = next(
        speaker
        for speaker in speakers
        if speaker != dominant_speaker
    )

    respondent_support_tags = []

    for tag in [
        "phone_no",
        "state_govt_change",
        "state_govt_change_party",
        "mla_choice",
        "mla_satisfaction",
        "mp_satisfaction",
        "cm_choice",
    ]:
        question = find_question(
            questions,
            tag,
        )

        if question is None:
            continue

        times = _speaker_core_time(
            question
        )

        respondent_time = (
            times.get(
                respondent_speaker,
                0.0,
            )
        )

        if respondent_time > 0.20:
            respondent_support_tags.append(
                tag
            )

    evidence.append(
        {
            "type": (
                "respondent_presence"
            ),
            "speaker_id": (
                respondent_speaker
            ),
            "supporting_tags": (
                respondent_support_tags
            ),
            "interpretation": (
                "Second speaker appears in "
                "multiple answer-bearing "
                "question windows."
            ),
        }
    )

    if len(
        respondent_support_tags
    ) < 2:
        confidence = "MODERATE"

    else:
        confidence = "STRONG"

    roles = {
        dominant_speaker: {
            "role": "agent",
            "confidence": confidence,
        },
        respondent_speaker: {
            "role": "respondent",
            "confidence": confidence,
        },
    }

    return {
        "status": "RESOLVED",
        "confidence": confidence,
        "speaker_totals_sec": (
            speaker_totals
        ),
        "roles": roles,
        "evidence": evidence,
        "limitations": [
            (
                "Global role mapping does "
                "not guarantee every "
                "individual diarization "
                "segment is correctly "
                "assigned."
            ),
            (
                "Short and overlapping "
                "segments remain unsafe "
                "for direct automation."
            ),
        ],
    }