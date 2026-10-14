import re
import unicodedata
from collections import defaultdict

from src.speaker_roles.models import (
    InferredSpeakerTurn,
    RawSpeakerTurn,
    SpeakerRoleInferenceResult,
)


SURVEY_QUESTION_MARKERS = [
    "क्या आप",
    "आपकी उम्र क्या",
    "आपकी उम्र",
    "आपके हिसाब से",
    "विधानसभा क्षेत्र",
    "राज्य सरकार",
    "मुख्यमंत्री",
    "किस पार्टी",
    "वोट देना",
    "देखना चाहते",
    "सबसे बड़ी समस्या",
    "उत्तर प्रदेश के निवासी",
]


AGENT_PROCEDURAL_MARKERS = [
    "ठीक है",
    "अगला सवाल",
    "कोई बात नहीं",
    "सर्वे के लिए धन्यवाद",
]


AGENT_DIRECTIVE_MARKERS = [
    "बोल दीजिए",
    "बोल दें",
    "बोल दो",
    "कह दीजिए",
    "कह दें",
    "चुनिए",
    "चुन लो",
    "सेलेक्ट",
    "select",
    "choose",
]


RESPONDENT_UNCERTAINTY_MARKERS = [
    "पता नहीं",
    "पता नही",
    "नहीं पता",
    "नही पता",
    "मालूम नहीं",
    "मालूम नही",
    "समझ नहीं आ रहा",
    "समझ नही आ रहा",
    "डिसाइड नहीं किया",
    "डिसाइड नही किया",
    "पक्का नहीं पता",
    "पक्का नही पता",
    "सोचा नहीं",
    "सोचा नही",
]


EXACT_SHORT_RESPONSES = [
    "हाँ",
    "हां",
    "नहीं",
    "नही",
    "जी",
]


def _normalize(
    text: str,
) -> str:
    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    text = text.lower().strip()

    text = re.sub(
        r"[^\w\s\u0900-\u097F]",
        " ",
        text,
    )

    return " ".join(
        text.split()
    )


def _contains_any(
    text: str,
    markers: list[str],
) -> bool:
    normalized = _normalize(
        text
    )

    return any(
        _normalize(marker) in normalized
        for marker in markers
    )


def _is_yes_no_followup(
    text: str,
) -> bool:
    normalized = _normalize(
        text
    )

    return (
        "हाँ या नहीं" in normalized
        or "हां या नहीं" in normalized
    )


def _looks_like_survey_question(
    text: str,
) -> bool:
    if _is_yes_no_followup(
        text
    ):
        return True

    return _contains_any(
        text,
        SURVEY_QUESTION_MARKERS,
    )


def _is_exact_short_response(
    text: str,
) -> bool:
    normalized = _normalize(
        text
    )

    return normalized in {
        _normalize(marker)
        for marker in EXACT_SHORT_RESPONSES
    }


def _looks_like_short_answer(
    text: str,
) -> bool:
    normalized = _normalize(
        text
    )

    if not normalized:
        return False

    if _contains_any(
        text,
        AGENT_PROCEDURAL_MARKERS,
    ):
        return False

    if _contains_any(
        text,
        AGENT_DIRECTIVE_MARKERS,
    ):
        return False

    if _looks_like_survey_question(
        text
    ):
        return False

    if _is_exact_short_response(
        text
    ):
        return True

    word_count = len(
        normalized.split()
    )

    return word_count <= 4


def _looks_like_mixed_turn(
    text: str,
) -> bool:
    normalized = _normalize(
        text
    )

    if not normalized:
        return False

    if (
        _looks_like_survey_question(text)
        and _contains_any(
            text,
            RESPONDENT_UNCERTAINTY_MARKERS,
        )
    ):
        return True

    marker = "ठीक है"

    marker_position = normalized.find(
        marker
    )

    if marker_position > 0:
        before = normalized[
            :marker_position
        ].strip()

        after = normalized[
            marker_position
            + len(marker):
        ].strip()

        if (
            before
            and after
            and _looks_like_survey_question(
                after
            )
        ):
            return True

    return False


def _infer_semantic_role(
    turn: RawSpeakerTurn,
) -> tuple[
    str,
    float,
    bool,
    list[str],
]:
    text = turn.text

    if not text.strip():
        return (
            "unknown",
            0.0,
            True,
            [
                "Transcript is empty."
            ],
        )

    if _looks_like_mixed_turn(
        text
    ):
        return (
            "unknown",
            0.40,
            True,
            [
                (
                    "Transcript appears to contain "
                    "speech from multiple dialogue roles."
                )
            ],
        )

    agent_score = 0.0
    respondent_score = 0.0

    reasons: list[str] = []

    if _looks_like_survey_question(
        text
    ):
        agent_score += 0.90

        reasons.append(
            "Text resembles a survey question."
        )

    if _contains_any(
        text,
        AGENT_PROCEDURAL_MARKERS,
    ):
        agent_score += 0.65

        reasons.append(
            "Text contains an agent procedural phrase."
        )

    if _contains_any(
        text,
        AGENT_DIRECTIVE_MARKERS,
    ):
        agent_score += 0.90

        reasons.append(
            "Text contains an agent instruction."
        )

    if _is_yes_no_followup(
        text
    ):
        agent_score += 0.40

        reasons.append(
            "Text presents a yes/no follow-up."
        )

    if _contains_any(
        text,
        RESPONDENT_UNCERTAINTY_MARKERS,
    ):
        respondent_score += 0.95

        reasons.append(
            "Text contains respondent uncertainty."
        )

    if _is_exact_short_response(
        text
    ):
        respondent_score += 0.65

        reasons.append(
            "Text is an explicit short answer."
        )

    elif _looks_like_short_answer(
        text
    ):
        respondent_score += 0.35

        reasons.append(
            "Text resembles a short answer."
        )

    if (
        agent_score == 0
        and respondent_score == 0
    ):
        return (
            "unknown",
            0.30,
            False,
            [
                "No strong semantic role evidence."
            ],
        )

    if agent_score > respondent_score:
        return (
            "agent",
            min(
                agent_score,
                1.0,
            ),
            False,
            reasons,
        )

    if respondent_score > agent_score:
        return (
            "respondent",
            min(
                respondent_score,
                1.0,
            ),
            False,
            reasons,
        )

    return (
        "unknown",
        0.50,
        True,
        reasons
        + [
            "Agent and respondent evidence are tied."
        ],
    )


def _apply_dialogue_context(
    turns: list[InferredSpeakerTurn],
) -> None:
    for index, turn in enumerate(
        turns
    ):
        if turn.review_required:
            continue

        previous = (
            turns[index - 1]
            if index > 0
            else None
        )

        if (
            previous is not None
            and previous.role == "agent"
            and _looks_like_short_answer(
                turn.text
            )
        ):
            turn.role = "respondent"

            turn.role_score = max(
                turn.role_score,
                0.85,
            )

            turn.reasons.append(
                "Short answer follows an agent turn."
            )

            continue

        if (
            previous is not None
            and previous.role == "respondent"
            and _looks_like_survey_question(
                turn.text
            )
        ):
            turn.role = "agent"

            turn.role_score = max(
                turn.role_score,
                0.90,
            )

            turn.reasons.append(
                (
                    "Survey question follows "
                    "respondent speech."
                )
            )


def _dominant_speaker_ids(
    turns: list[InferredSpeakerTurn],
) -> tuple[
    str | None,
    str | None,
]:
    role_counts = {
        "agent": defaultdict(int),
        "respondent": defaultdict(int),
    }

    for turn in turns:
        if turn.review_required:
            continue

        if turn.role_score < 0.70:
            continue

        if turn.role not in role_counts:
            continue

        role_counts[
            turn.role
        ][
            turn.speaker_id
        ] += 1

    def dominant(
        role: str,
    ) -> str | None:
        counts = role_counts[
            role
        ]

        if not counts:
            return None

        return max(
            counts.items(),
            key=lambda item: item[1],
        )[0]

    return (
        dominant("agent"),
        dominant("respondent"),
    )


def _apply_diarization_consistency(
    turns: list[InferredSpeakerTurn],
    dominant_agent_id: str | None,
    dominant_respondent_id: str | None,
) -> None:
    for turn in turns:
        if turn.review_required:
            continue

        if turn.role != "unknown":
            continue

        if (
            dominant_agent_id is not None
            and turn.speaker_id
            == dominant_agent_id
        ):
            turn.role = "agent"

            turn.role_score = 0.60

            turn.reasons.append(
                (
                    "Diarization speaker usually "
                    "corresponds to the agent."
                )
            )

            continue

        if (
            dominant_respondent_id is not None
            and turn.speaker_id
            == dominant_respondent_id
        ):
            turn.role = "respondent"

            turn.role_score = 0.60

            turn.reasons.append(
                (
                    "Diarization speaker usually "
                    "corresponds to the respondent."
                )
            )


def infer_speaker_roles(
    raw_turns: list[RawSpeakerTurn],
) -> SpeakerRoleInferenceResult:
    inferred: list[
        InferredSpeakerTurn
    ] = []

    for raw_turn in raw_turns:
        (
            role,
            role_score,
            review_required,
            reasons,
        ) = _infer_semantic_role(
            raw_turn
        )

        inferred.append(
            InferredSpeakerTurn(
                segment_id=raw_turn.segment_id,
                speaker_id=raw_turn.speaker_id,
                text=raw_turn.text,
                role=role,
                role_score=role_score,
                start_sec=raw_turn.start_sec,
                end_sec=raw_turn.end_sec,
                review_required=review_required,
                reasons=reasons,
            )
        )

    _apply_dialogue_context(
        inferred
    )

    (
        dominant_agent_id,
        dominant_respondent_id,
    ) = _dominant_speaker_ids(
        inferred
    )

    _apply_diarization_consistency(
        turns=inferred,
        dominant_agent_id=(
            dominant_agent_id
        ),
        dominant_respondent_id=(
            dominant_respondent_id
        ),
    )

    _apply_dialogue_context(
        inferred
    )

    return SpeakerRoleInferenceResult(
        turns=inferred,
        dominant_agent_speaker_id=(
            dominant_agent_id
        ),
        dominant_respondent_speaker_id=(
            dominant_respondent_id
        ),
    )