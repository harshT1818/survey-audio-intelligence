import re
import unicodedata

from src.evidence_quality.models import (
    EvidenceQualityResult,
)
from src.resolver.closed_set import (
    resolve_closed_set_answer,
)
from src.resolver.models import (
    CanonicalOption,
)


QUESTION_LIKE_MARKERS = [
    "क्या आप",
    "आपकी उम्र क्या",
    "आपके हिसाब से",
    "किस पार्टी",
    "मुख्यमंत्री",
    "विधानसभा क्षेत्र",
    "सबसे बड़ी समस्या",
    "वोट देना",
    "देखना चाहते",
]


LOW_INFORMATION_TEXTS = {
    "",
    "ठीक है",
    "ठीक",
    "जी",
}


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


def _looks_like_question(
    text: str,
) -> bool:
    normalized = _normalize(
        text
    )

    return any(
        _normalize(marker)
        in normalized
        for marker
        in QUESTION_LIKE_MARKERS
    )


def _is_low_information(
    text: str,
) -> bool:
    normalized = _normalize(
        text
    )

    return normalized in {
        _normalize(value)
        for value
        in LOW_INFORMATION_TEXTS
    }


def evaluate_answer_evidence(
    raw_text: str,
    options: list[CanonicalOption],
    stored_option: str | None = None,
    upstream_review_required: bool = False,
    source_is_mixed: bool = False,
    prefill_threshold: float = 0.72,
    auto_fill_threshold: float = 0.90,
) -> EvidenceQualityResult:

    if not raw_text.strip():
        return EvidenceQualityResult(
            raw_text=raw_text,
            evidence_status="UNUSABLE",
            automation_status="NO_EVIDENCE",
            review_required=True,
            reasons=[
                "Transcript is empty."
            ],
        )

    if source_is_mixed:
        return EvidenceQualityResult(
            raw_text=raw_text,
            evidence_status="WEAK",
            automation_status="HUMAN_REVIEW",
            review_required=True,
            reasons=[
                (
                    "Source segment contains "
                    "multiple dialogue roles."
                )
            ],
        )

    if upstream_review_required:
        return EvidenceQualityResult(
            raw_text=raw_text,
            evidence_status="WEAK",
            automation_status="HUMAN_REVIEW",
            review_required=True,
            reasons=[
                (
                    "Upstream speaker or segment "
                    "analysis requires review."
                )
            ],
        )

    if _is_low_information(
        raw_text
    ):
        return EvidenceQualityResult(
            raw_text=raw_text,
            evidence_status="UNUSABLE",
            automation_status="NO_EVIDENCE",
            review_required=True,
            reasons=[
                (
                    "Transcript does not contain "
                    "enough answer information."
                )
            ],
        )

    if _looks_like_question(
        raw_text
    ):
        return EvidenceQualityResult(
            raw_text=raw_text,
            evidence_status="WEAK",
            automation_status="HUMAN_REVIEW",
            review_required=True,
            reasons=[
                (
                    "Answer evidence also looks "
                    "like survey-question speech."
                )
            ],
        )

    resolution = resolve_closed_set_answer(
        raw_text=raw_text,
        options=options,
        stored_option=stored_option,
    )

    if resolution.status == "UNCERTAIN":
        return EvidenceQualityResult(
            raw_text=raw_text,
            evidence_status="WEAK",
            automation_status="HUMAN_REVIEW",
            resolved_option=(
                resolution.resolved_option
            ),
            resolution_status=(
                resolution.status
            ),
            resolution_score=(
                resolution.confidence
            ),
            review_required=True,
            reasons=[
                (
                    "Transcript could not be "
                    "reliably resolved to one "
                    "survey option."
                )
            ],
        )

    if (
        resolution.confidence
        >= auto_fill_threshold
    ):
        return EvidenceQualityResult(
            raw_text=raw_text,
            evidence_status="STRONG",
            automation_status=(
                "AUTO_FILL_CANDIDATE"
            ),
            resolved_option=(
                resolution.resolved_option
            ),
            resolution_status=(
                resolution.status
            ),
            resolution_score=(
                resolution.confidence
            ),
            review_required=False,
            reasons=[
                (
                    "Transcript has a strong "
                    "single-option match."
                )
            ],
        )

    if (
        resolution.confidence
        >= prefill_threshold
    ):
        return EvidenceQualityResult(
            raw_text=raw_text,
            evidence_status="MODERATE",
            automation_status=(
                "PREFILL_CANDIDATE"
            ),
            resolved_option=(
                resolution.resolved_option
            ),
            resolution_status=(
                resolution.status
            ),
            resolution_score=(
                resolution.confidence
            ),
            review_required=True,
            reasons=[
                (
                    "Transcript has a plausible "
                    "option match but should not "
                    "be fully automated alone."
                )
            ],
        )

    return EvidenceQualityResult(
        raw_text=raw_text,
        evidence_status="WEAK",
        automation_status="HUMAN_REVIEW",
        resolved_option=(
            resolution.resolved_option
        ),
        resolution_status=(
            resolution.status
        ),
        resolution_score=(
            resolution.confidence
        ),
        review_required=True,
        reasons=[
            (
                "Option match is too weak for "
                "automatic use."
            )
        ],
    )