import re
import unicodedata

from rapidfuzz import fuzz

from src.resolver.models import (
    AnswerResolution,
    CanonicalOption,
    ResolutionCandidate,
)


UNCERTAINTY_MARKERS = [
    "पता नहीं",
    "पता नही",
    "नहीं पता",
    "नही पता",
    "मालूम नहीं",
    "मालूम नही",
    "नहीं मालूम",
    "नही मालूम",
    "पता नहीं है",
    "मालूम नहीं है",
    "मुझे पता नहीं",
    "मुझे मालूम नहीं",
    "कह नहीं सकता",
    "कह नही सकता",
    "बता नहीं सकता",
    "बता नही सकता",
    "सोचा नहीं",
    "सोचा नही",
    "याद नहीं",
    "याद नही",
    "don't know",
    "dont know",
    "do not know",
    "not sure",
    "no idea",
    "cannot say",
    "can't say",
    "cant say",
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


def _candidate_texts(
    option: CanonicalOption,
) -> list[str]:
    values = [
        option.value,
        *option.labels,
        *option.aliases,
    ]

    return [
        value
        for value in values
        if value.strip()
    ]


def _is_uncertain_response(
    raw_text: str,
) -> bool:
    normalized_text = _normalize(
        raw_text
    )

    return any(
        _normalize(marker) in normalized_text
        for marker in UNCERTAINTY_MARKERS
    )


def resolve_closed_set_answer(
    raw_text: str,
    options: list[CanonicalOption],
    stored_option: str | None = None,
    minimum_score: float = 0.65,
    ambiguity_margin: float = 0.08,
) -> AnswerResolution:

    if not raw_text.strip() or not options:
        return AnswerResolution(
            raw_text=raw_text,
            stored_option=stored_option,
            status="UNCERTAIN",
            confidence=0,
        )

    # ---------------------------------------------------------
    # Handle explicit uncertainty BEFORE option matching.
    #
    # Example:
    #
    # "मुझे पता नहीं"
    #
    # contains "नहीं", but that does NOT mean the respondent
    # selected the "No" option.
    # ---------------------------------------------------------

    if _is_uncertain_response(
        raw_text
    ):
        return AnswerResolution(
            raw_text=raw_text,
            stored_option=stored_option,
            status="UNCERTAIN",
            confidence=0,
            candidates=[],
        )

    normalized_raw = _normalize(
        raw_text
    )

    scored: list[ResolutionCandidate] = []

    for option in options:
        best_score = 0.0
        best_text = option.value

        for candidate_text in _candidate_texts(
            option
        ):
            score = (
                fuzz.WRatio(
                    normalized_raw,
                    _normalize(candidate_text),
                )
                / 100
            )

            if score > best_score:
                best_score = score
                best_text = candidate_text

        scored.append(
            ResolutionCandidate(
                option=option.value,
                matched_text=best_text,
                score=round(
                    best_score,
                    4,
                ),
            )
        )

    scored.sort(
        key=lambda candidate: candidate.score,
        reverse=True,
    )

    best = scored[0]

    second_score = (
        scored[1].score
        if len(scored) > 1
        else 0
    )

    ambiguous = (
        best.score - second_score
        < ambiguity_margin
    )

    if (
        best.score < minimum_score
        or ambiguous
    ):
        return AnswerResolution(
            raw_text=raw_text,
            stored_option=stored_option,
            status="UNCERTAIN",
            confidence=best.score,
            candidates=scored[:3],
        )

    if stored_option is None:
        status = "MATCH"

    elif (
        _normalize(best.option)
        == _normalize(stored_option)
    ):
        status = "MATCH"

    else:
        status = "MISMATCH"

    return AnswerResolution(
        raw_text=raw_text,
        resolved_option=best.option,
        stored_option=stored_option,
        status=status,
        confidence=best.score,
        candidates=scored[:3],
    )