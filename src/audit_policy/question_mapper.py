from dataclasses import dataclass

from src.audit_policy.models import (
    AuditTagPolicy,
    DispositionNode,
)
from src.question_validation.models import (
    QuestionValidationResult,
)


@dataclass
class QuestionDispositionSuggestion:
    disposition_id: int | float | str | None
    disposition_text: str | None
    status: str
    review_required: bool
    reason: str


def _find_disposition(
    nodes: list[DispositionNode],
    text: str,
) -> DispositionNode | None:

    for node in nodes:
        if node.text.strip().lower() == text.strip().lower():
            return node

        found = _find_disposition(
            node.children,
            text,
        )

        if found is not None:
            return found

    return None


def map_question_validation_to_disposition(
    validation: QuestionValidationResult,
    tag_policy: AuditTagPolicy,
    asked_right_text: str = "Asked Right",
) -> QuestionDispositionSuggestion:

    if not tag_policy.question_validation.enabled:
        return QuestionDispositionSuggestion(
            disposition_id=None,
            disposition_text=None,
            status="NO_MAPPING",
            review_required=False,
            reason="Question validation is disabled for this tag.",
        )

    if validation.status != "ASKED_RIGHT":
        return QuestionDispositionSuggestion(
            disposition_id=None,
            disposition_text=None,
            status="UNCERTAIN",
            review_required=True,
            reason=(
                "Question evidence is not strong enough "
                "for automatic disposition selection."
            ),
        )

    disposition = _find_disposition(
        tag_policy.question_validation.dispositions,
        asked_right_text,
    )

    if disposition is None:
        return QuestionDispositionSuggestion(
            disposition_id=None,
            disposition_text=None,
            status="NO_MAPPING",
            review_required=True,
            reason=(
                f"Configured disposition "
                f"'{asked_right_text}' was not found."
            ),
        )

    return QuestionDispositionSuggestion(
        disposition_id=disposition.id,
        disposition_text=disposition.text,
        status="SUGGESTED",
        review_required=False,
        reason="Question was confidently classified as Asked Right.",
    )