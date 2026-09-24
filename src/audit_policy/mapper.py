from dataclasses import dataclass

from src.audit_policy.models import (
    AuditTagPolicy,
    DispositionNode,
)
from src.resolver.models import AnswerResolution


@dataclass
class DispositionSuggestion:
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


def map_answer_resolution_to_disposition(
    resolution: AnswerResolution,
    tag_policy: AuditTagPolicy,
    match_disposition_text: str = "Asked Right",
    mismatch_disposition_text: str = "Mismatch",
) -> DispositionSuggestion:

    if not tag_policy.answer_validation.enabled:
        return DispositionSuggestion(
            disposition_id=None,
            disposition_text=None,
            status="NO_MAPPING",
            review_required=True,
            reason="Answer validation is disabled for this audit tag.",
        )

    if resolution.status == "UNCERTAIN":
        return DispositionSuggestion(
            disposition_id=None,
            disposition_text=None,
            status="UNCERTAIN",
            review_required=True,
            reason="Answer resolution was uncertain.",
        )

    target_text = (
        match_disposition_text
        if resolution.status == "MATCH"
        else mismatch_disposition_text
    )

    disposition = _find_disposition(
        tag_policy.answer_validation.dispositions,
        target_text,
    )

    if disposition is None:
        return DispositionSuggestion(
            disposition_id=None,
            disposition_text=None,
            status="NO_MAPPING",
            review_required=True,
            reason=(
                f"Configured disposition '{target_text}' "
                "was not found."
            ),
        )

    return DispositionSuggestion(
        disposition_id=disposition.id,
        disposition_text=disposition.text,
        status="SUGGESTED",
        review_required=False,
        reason=(
            f"Answer resolution status was "
            f"{resolution.status}."
        ),
    )