import re
import unicodedata

from src.evidence_quality.corroboration_models import (
    CorroboratedEvidenceResult,
    CorroborationTurn,
    TurnEvidence,
)
from src.evidence_quality.gate import (
    evaluate_answer_evidence,
)
from src.resolver.closed_set import (
    resolve_closed_set_answer,
)
from src.resolver.models import (
    CanonicalOption,
)


AFFIRMATIVE_RESPONSES = {
    "हाँ",
    "हां",
    "जी",
    "जी हाँ",
    "जी हां",
    "yes",
}


AGENT_DIRECTIVE_MARKERS = [
    "बोल दीजिए",
    "बोल दें",
    "बोल दो",
    "कह दीजिए",
    "कह दें",
    "चुनिए",
    "चुन लो",
    "select",
    "choose",
]


QUESTION_MARKERS = [
    "क्या",
    "कौन",
    "किस",
    "किसे",
    "कहाँ",
    "कितना",
    "कितनी",
    "कितने",
    "वोट देना",
    "देखना चाहते",
    "मुख्यमंत्री",
    "विधानसभा क्षेत्र",
    "समस्या क्या",
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


def _same_option(
    left: str | None,
    right: str | None,
) -> bool:
    if (
        left is None
        or right is None
    ):
        return False

    return (
        _normalize(left)
        == _normalize(right)
    )


def _contains_any(
    text: str,
    markers: list[str],
) -> bool:
    normalized = _normalize(
        text
    )

    return any(
        _normalize(marker)
        in normalized
        for marker
        in markers
    )


def _is_affirmative(
    text: str,
) -> bool:
    return (
        _normalize(text)
        in {
            _normalize(value)
            for value
            in AFFIRMATIVE_RESPONSES
        }
    )


def _agent_turn_can_corroborate(
    text: str,
) -> bool:
    if not text.strip():
        return False

    if _contains_any(
        text,
        AGENT_DIRECTIVE_MARKERS,
    ):
        return False

    if _contains_any(
        text,
        QUESTION_MARKERS,
    ):
        return False

    word_count = len(
        _normalize(
            text
        ).split()
    )

    return (
        0 < word_count <= 6
    )


def _resolution_status(
    resolved_option: str | None,
    stored_option: str | None,
) -> str | None:
    if resolved_option is None:
        return None

    if stored_option is None:
        return "RESOLVED"

    if _same_option(
        resolved_option,
        stored_option,
    ):
        return "MATCH"

    return "MISMATCH"


def corroborate_answer_evidence(
    turns: list[CorroborationTurn],
    options: list[CanonicalOption],
    stored_option: str | None = None,
) -> CorroboratedEvidenceResult:

    if not turns:
        return CorroboratedEvidenceResult(
            stored_option=stored_option,
            evidence_strength="UNUSABLE",
            automation_status="NO_EVIDENCE",
            review_required=True,
            reasons=[
                "No dialogue turns were provided."
            ],
        )

    turn_evidence: list[
        TurnEvidence
    ] = []

    unsafe_turn_ids: list[str] = []

    direct_candidates: dict[
        str,
        list[
            tuple[
                CorroborationTurn,
                str,
            ]
        ],
    ] = {}

    contextual_candidates: dict[
        str,
        list[str],
    ] = {}

    strong_options: set[str] = set()

    moderate_options: set[str] = set()

    for turn in turns:
        if (
            turn.role == "unknown"
            or turn.upstream_review_required
            or turn.source_is_mixed
        ):
            unsafe_turn_ids.append(
                turn.turn_id
            )

        if turn.role != "respondent":
            turn_evidence.append(
                TurnEvidence(
                    turn_id=turn.turn_id,
                    role=turn.role,
                    raw_text=turn.text,
                )
            )

            continue

        result = evaluate_answer_evidence(
            raw_text=turn.text,
            options=options,
            stored_option=stored_option,
            upstream_review_required=(
                turn.upstream_review_required
            ),
            source_is_mixed=(
                turn.source_is_mixed
            ),
        )

        turn_evidence.append(
            TurnEvidence(
                turn_id=turn.turn_id,
                role=turn.role,
                raw_text=turn.text,
                resolved_option=(
                    result.resolved_option
                ),
                evidence_status=(
                    result.evidence_status
                ),
                automation_status=(
                    result.automation_status
                ),
                resolution_score=(
                    result.resolution_score
                ),
            )
        )

        if (
            result.resolved_option
            is None
        ):
            continue

        if (
            result.automation_status
            not in {
                "AUTO_FILL_CANDIDATE",
                "PREFILL_CANDIDATE",
            }
        ):
            continue

        option = (
            result.resolved_option
        )

        direct_candidates.setdefault(
            option,
            [],
        ).append(
            (
                turn,
                result.evidence_status,
            )
        )

        if (
            result.automation_status
            == "AUTO_FILL_CANDIDATE"
        ):
            strong_options.add(
                option
            )

        elif (
            result.automation_status
            == "PREFILL_CANDIDATE"
        ):
            moderate_options.add(
                option
            )

    for index in range(
        1,
        len(turns),
    ):
        respondent_turn = turns[
            index
        ]

        if (
            respondent_turn.role
            != "respondent"
        ):
            continue

        if not _is_affirmative(
            respondent_turn.text
        ):
            continue

        agent_turn = turns[
            index - 1
        ]

        if agent_turn.role != "agent":
            continue

        if (
            agent_turn.upstream_review_required
            or agent_turn.source_is_mixed
        ):
            continue

        if not _agent_turn_can_corroborate(
            agent_turn.text
        ):
            continue

        agent_resolution = (
            resolve_closed_set_answer(
                raw_text=agent_turn.text,
                options=options,
                stored_option=stored_option,
            )
        )

        if (
            agent_resolution.status
            == "UNCERTAIN"
        ):
            continue

        if (
            agent_resolution.resolved_option
            is None
        ):
            continue

        if (
            agent_resolution.confidence
            < 0.90
        ):
            continue

        option = (
            agent_resolution.resolved_option
        )

        contextual_candidates.setdefault(
            option,
            [],
        ).extend(
            [
                agent_turn.turn_id,
                respondent_turn.turn_id,
            ]
        )

    candidate_options = set(
        direct_candidates.keys()
    )

    candidate_options.update(
        contextual_candidates.keys()
    )

    if not candidate_options:
        return CorroboratedEvidenceResult(
            stored_option=stored_option,
            evidence_strength="WEAK",
            automation_status="HUMAN_REVIEW",
            unsafe_turn_ids=(
                unsafe_turn_ids
            ),
            turn_evidence=turn_evidence,
            review_required=True,
            reasons=[
                (
                    "No survey option had enough "
                    "respondent or contextual support."
                )
            ],
        )

    if len(candidate_options) > 1:
        conflicting_turn_ids = []

        for (
            option,
            support,
        ) in direct_candidates.items():
            for turn, _ in support:
                conflicting_turn_ids.append(
                    turn.turn_id
                )

        for (
            option,
            support_ids,
        ) in contextual_candidates.items():
            conflicting_turn_ids.extend(
                support_ids
            )

        return CorroboratedEvidenceResult(
            stored_option=stored_option,
            evidence_strength="WEAK",
            automation_status="HUMAN_REVIEW",
            conflicting_turn_ids=sorted(
                set(
                    conflicting_turn_ids
                )
            ),
            unsafe_turn_ids=(
                unsafe_turn_ids
            ),
            turn_evidence=turn_evidence,
            review_required=True,
            reasons=[
                (
                    "Different dialogue turns support "
                    "different survey options."
                )
            ],
        )

    selected_option = next(
        iter(
            candidate_options
        )
    )

    direct_support = (
        direct_candidates.get(
            selected_option,
            [],
        )
    )

    direct_support_turn_ids = [
        turn.turn_id
        for turn, _
        in direct_support
    ]

    contextual_support_turn_ids = sorted(
        set(
            contextual_candidates.get(
                selected_option,
                [],
            )
        )
    )

    has_strong_direct_support = any(
        strength == "STRONG"
        for _, strength
        in direct_support
    )

    has_moderate_direct_support = any(
        strength == "MODERATE"
        for _, strength
        in direct_support
    )

    resolution_status = (
        _resolution_status(
            selected_option,
            stored_option,
        )
    )

    if has_strong_direct_support:
        if unsafe_turn_ids:
            return CorroboratedEvidenceResult(
                resolved_option=(
                    selected_option
                ),
                stored_option=(
                    stored_option
                ),
                resolution_status=(
                    resolution_status
                ),
                evidence_strength="MODERATE",
                automation_status=(
                    "PREFILL_CANDIDATE"
                ),
                direct_support_turn_ids=(
                    direct_support_turn_ids
                ),
                contextual_support_turn_ids=(
                    contextual_support_turn_ids
                ),
                unsafe_turn_ids=(
                    unsafe_turn_ids
                ),
                turn_evidence=turn_evidence,
                review_required=True,
                reasons=[
                    (
                        "Strong respondent evidence "
                        "exists, but the question window "
                        "also contains unreliable context."
                    )
                ],
            )

        return CorroboratedEvidenceResult(
            resolved_option=(
                selected_option
            ),
            stored_option=stored_option,
            resolution_status=(
                resolution_status
            ),
            evidence_strength="STRONG",
            automation_status=(
                "AUTO_FILL_CANDIDATE"
            ),
            direct_support_turn_ids=(
                direct_support_turn_ids
            ),
            contextual_support_turn_ids=(
                contextual_support_turn_ids
            ),
            unsafe_turn_ids=(
                unsafe_turn_ids
            ),
            turn_evidence=turn_evidence,
            review_required=False,
            reasons=[
                (
                    "At least one clean respondent "
                    "turn strongly supports the "
                    "resolved survey option."
                )
            ],
        )

    if (
        has_moderate_direct_support
        or contextual_support_turn_ids
    ):
        return CorroboratedEvidenceResult(
            resolved_option=(
                selected_option
            ),
            stored_option=stored_option,
            resolution_status=(
                resolution_status
            ),
            evidence_strength="MODERATE",
            automation_status=(
                "PREFILL_CANDIDATE"
            ),
            direct_support_turn_ids=(
                direct_support_turn_ids
            ),
            contextual_support_turn_ids=(
                contextual_support_turn_ids
            ),
            unsafe_turn_ids=(
                unsafe_turn_ids
            ),
            turn_evidence=turn_evidence,
            review_required=True,
            reasons=[
                (
                    "The option has useful supporting "
                    "evidence, but not enough clean "
                    "respondent evidence for auto-fill."
                )
            ],
        )

    return CorroboratedEvidenceResult(
        resolved_option=(
            selected_option
        ),
        stored_option=stored_option,
        resolution_status=(
            resolution_status
        ),
        evidence_strength="WEAK",
        automation_status="HUMAN_REVIEW",
        direct_support_turn_ids=(
            direct_support_turn_ids
        ),
        contextual_support_turn_ids=(
            contextual_support_turn_ids
        ),
        unsafe_turn_ids=(
            unsafe_turn_ids
        ),
        turn_evidence=turn_evidence,
        review_required=True,
        reasons=[
            (
                "Available support is not strong "
                "enough for automated use."
            )
        ],
    )