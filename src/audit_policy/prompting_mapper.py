from dataclasses import dataclass

from src.audit_policy.models import (
    AuditTagPolicy,
    DispositionNode,
)
from src.prompting.models import PromptingEvidence
from src.resolver.models import AnswerResolution


@dataclass
class PromptingDispositionSuggestion:
    disposition_id: int | float | str | None
    disposition_text: str | None
    disposition_path: list[str]

    status: str
    review_required: bool
    reason: str


def _find_child(
    nodes: list[DispositionNode],
    text: str,
) -> DispositionNode | None:
    target = text.strip().lower()

    for node in nodes:
        if node.text.strip().lower() == target:
            return node

    return None


def _find_disposition_path(
    nodes: list[DispositionNode],
    path: list[str],
) -> DispositionNode | None:
    if not path:
        return None

    current_nodes = nodes
    current_node = None

    for path_part in path:
        current_node = _find_child(
            current_nodes,
            path_part,
        )

        if current_node is None:
            return None

        current_nodes = current_node.children

    return current_node


def map_prompting_answer_disposition(
    resolution: AnswerResolution,
    prompting: PromptingEvidence,
    tag_policy: AuditTagPolicy,
    no_prompting_path: list[str],
    prompting_path: list[str],
) -> PromptingDispositionSuggestion:

    if not tag_policy.answer_validation.enabled:
        return PromptingDispositionSuggestion(
            disposition_id=None,
            disposition_text=None,
            disposition_path=[],
            status="NO_MAPPING",
            review_required=False,
            reason=(
                "Answer validation is disabled "
                "for this audit tag."
            ),
        )

    if resolution.status == "UNCERTAIN":
        return PromptingDispositionSuggestion(
            disposition_id=None,
            disposition_text=None,
            disposition_path=[],
            status="UNCERTAIN",
            review_required=True,
            reason=(
                "Answer resolution is uncertain, "
                "so a prompting-aware disposition "
                "cannot be selected safely."
            ),
        )

    if resolution.status != "MATCH":
        return PromptingDispositionSuggestion(
            disposition_id=None,
            disposition_text=None,
            disposition_path=[],
            status="UNCERTAIN",
            review_required=True,
            reason=(
                "The spoken answer does not match "
                "the stored answer."
            ),
        )

    if prompting.status == "PROMPTING_EVIDENCE":
        selected_path = prompting_path

    elif prompting.status == "NO_PROMPTING_EVIDENCE":
        selected_path = no_prompting_path

    else:
        return PromptingDispositionSuggestion(
            disposition_id=None,
            disposition_text=None,
            disposition_path=[],
            status="UNCERTAIN",
            review_required=True,
            reason=(
                "Prompting classification is uncertain, "
                "so no prompting-aware disposition "
                "was selected."
            ),
        )

    disposition = _find_disposition_path(
        nodes=tag_policy.answer_validation.dispositions,
        path=selected_path,
    )

    if disposition is None:
        return PromptingDispositionSuggestion(
            disposition_id=None,
            disposition_text=None,
            disposition_path=selected_path,
            status="NO_MAPPING",
            review_required=True,
            reason=(
                "The requested disposition path "
                "was not found in the configured "
                "answer-validation tree."
            ),
        )

    return PromptingDispositionSuggestion(
        disposition_id=disposition.id,
        disposition_text=disposition.text,
        disposition_path=selected_path,
        status="SUGGESTED",
        review_required=False,
        reason=(
            "Answer matched the stored response and "
            "prompting evidence was sufficiently clear "
            "to select the configured disposition."
        ),
    )