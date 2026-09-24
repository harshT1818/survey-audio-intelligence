import re
import unicodedata

from rapidfuzz import fuzz

from src.question_validation.models import (
    QuestionValidationResult,
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.lower().strip()

    text = re.sub(
        r"[^\w\s\u0900-\u097F]",
        " ",
        text,
    )

    return " ".join(text.split())


def validate_question_text(
    expected_question: str,
    transcript_text: str,
    asked_right_threshold: float = 0.82,
) -> QuestionValidationResult:

    if not expected_question.strip():
        return QuestionValidationResult(
            expected_question=expected_question,
            transcript_text=transcript_text,
            status="NO_EXPECTED_QUESTION",
            confidence=0,
            review_required=True,
            reason="Configured question text is missing.",
        )

    if not transcript_text.strip():
        return QuestionValidationResult(
            expected_question=expected_question,
            transcript_text=transcript_text,
            status="UNCERTAIN",
            confidence=0,
            review_required=True,
            reason="No transcript evidence was provided.",
        )

    expected = _normalize(expected_question)
    transcript = _normalize(transcript_text)

    score = fuzz.partial_ratio(
        expected,
        transcript,
    ) / 100

    score = round(score, 4)

    if score >= asked_right_threshold:
        return QuestionValidationResult(
            expected_question=expected_question,
            transcript_text=transcript_text,
            status="ASKED_RIGHT",
            confidence=score,
            matched_text=transcript_text,
            review_required=False,
            reason="Configured question strongly matches transcript evidence.",
        )

    return QuestionValidationResult(
        expected_question=expected_question,
        transcript_text=transcript_text,
        status="UNCERTAIN",
        confidence=score,
        matched_text=transcript_text,
        review_required=True,
        reason="Question similarity is not high enough for automatic validation.",
    )