import re
import unicodedata

from src.prompting.models import PromptingEvidence
from src.resolver.models import CanonicalOption


UNCERTAINTY_MARKERS = [
    "पता नहीं",
    "नहीं पता",
    "मालूम नहीं",
    "नहीं मालूम",
    "सोचा नहीं",
    "कह नहीं सकता",
    "पता नही",
    "मालूम नही",
    "dont know",
    "don't know",
    "not sure",
]


DIRECTIVE_MARKERS = [
    "बोल दीजिए",
    "बोल दीजिये",
    "बोल दो",
    "बोलिये",
    "बोलिए",
    "कह दीजिए",
    "कह दीजिये",
    "कह दो",
    "कर दीजिए",
    "कर दीजिये",
    "कर दो",
    "लगा दो",
    "चुन लो",
    "choose",
    "select",
    "say",
]


def _normalize(text: str) -> str:
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
    normalized = _normalize(text)

    return any(
        _normalize(marker) in normalized
        for marker in markers
    )


def _matching_options(
    text: str,
    options: list[CanonicalOption],
) -> list[str]:
    normalized_text = _normalize(text)

    matches: list[str] = []

    for option in options:
        candidate_texts = [
            option.value,
            *option.labels,
            *option.aliases,
        ]

        for candidate in candidate_texts:
            normalized_candidate = _normalize(
                candidate
            )

            if (
                normalized_candidate
                and normalized_candidate
                in normalized_text
            ):
                matches.append(
                    option.value
                )
                break

    return list(
        dict.fromkeys(matches)
    )


def detect_prompting(
    respondent_text: str,
    agent_followup_text: str,
    options: list[CanonicalOption],
) -> PromptingEvidence:

    if not agent_followup_text.strip():
        return PromptingEvidence(
            status="NO_PROMPTING_EVIDENCE",
            confidence=0.95,
            agent_followup_text=agent_followup_text,
            respondent_text=respondent_text,
            suggested_option=None,
            review_required=False,
            reason=(
                "No agent follow-up speech was provided "
                "after the respondent answer."
            ),
        )

    respondent_uncertain = _contains_any(
        respondent_text,
        UNCERTAINTY_MARKERS,
    )

    directive_present = _contains_any(
        agent_followup_text,
        DIRECTIVE_MARKERS,
    )

    matching_options = _matching_options(
        agent_followup_text,
        options,
    )

    if (
        respondent_uncertain
        and directive_present
        and len(matching_options) == 1
    ):
        return PromptingEvidence(
            status="PROMPTING_EVIDENCE",
            confidence=0.9,
            agent_followup_text=agent_followup_text,
            respondent_text=respondent_text,
            suggested_option=matching_options[0],
            review_required=False,
            reason=(
                "Respondent expressed uncertainty and "
                "the agent subsequently directed them "
                "toward one specific answer option."
            ),
        )

    return PromptingEvidence(
        status="UNCERTAIN",
        confidence=0.5,
        agent_followup_text=agent_followup_text,
        respondent_text=respondent_text,
        suggested_option=(
            matching_options[0]
            if len(matching_options) == 1
            else None
        ),
        review_required=True,
        reason=(
            "The available dialogue does not provide "
            "strong enough evidence to classify prompting."
        ),
    )