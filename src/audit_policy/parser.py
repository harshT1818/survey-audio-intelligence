import json
from typing import Any

from src.audit_policy.models import (
    AuditProjectPolicy,
    AuditTagPolicy,
    DispositionNode,
    ValidationPolicy,
)


def _parse_disposition_node(raw: dict[str, Any]) -> DispositionNode:
    children = [
        _parse_disposition_node(child)
        for child in raw.get("sublist", [])
        if child.get("text")
    ]

    return DispositionNode(
        id=raw.get("id", ""),
        text=raw.get("text", "").strip(),
        comments_required=bool(raw.get("comments", False)),
        children=children,
    )


def _parse_disposition_list(
    raw_items: list[dict[str, Any]],
) -> list[DispositionNode]:
    return [
        _parse_disposition_node(item)
        for item in raw_items
        if item.get("text")
    ]


def _parse_tag(raw_tag: dict[str, Any]) -> AuditTagPolicy:
    raw_disposition = raw_tag.get("desposition", "{}")

    if isinstance(raw_disposition, str):
        disposition_config = json.loads(raw_disposition)
    else:
        disposition_config = raw_disposition

    question_config = disposition_config.get("question", {})
    breakdown = disposition_config.get("primary_breakdown", {})

    if not isinstance(breakdown, dict):
        breakdown = {}

    question_validation = ValidationPolicy(
        enabled=bool(question_config.get("ques_validation", False)),
        validation_type=question_config.get("ques_validation_type"),
        dispositions=_parse_disposition_list(
            breakdown.get("quesVal", [])
        ),
    )

    answer_validation = ValidationPolicy(
        enabled=bool(question_config.get("ans_validation", False)),
        validation_type=question_config.get("ans_validation_type"),
        dispositions=_parse_disposition_list(
            breakdown.get("ansVal", [])
        ),
    )

    return AuditTagPolicy(
        tag=raw_tag["tag"],
        placeholder=raw_tag.get("placeholder", raw_tag["tag"]),
        project_code=raw_tag["project_code"],
        active=bool(raw_tag.get("is_active", False)),
        order=int(raw_tag.get("order", 0)),
        tag_type=raw_tag.get("tag_type", ""),
        question_tag_id=raw_tag.get("question_tag_id"),
        question_validation=question_validation,
        answer_validation=answer_validation,
    )


def parse_audit_project(
    payload: dict[str, Any],
    active_only: bool = True,
) -> AuditProjectPolicy:
    data = payload.get("data", payload)

    project_code = data["project_code"]
    project_name = data.get("project_name")

    parsed_tags: dict[str, AuditTagPolicy] = {}

    for raw_tag in data.get("project_tags", []):
        tag = _parse_tag(raw_tag)

        if active_only and not tag.active:
            continue

        parsed_tags[tag.tag] = tag

    return AuditProjectPolicy(
        project_code=project_code,
        project_name=project_name,
        tags=parsed_tags,
    )


def load_audit_project(
    file_path: str,
    active_only: bool = True,
) -> AuditProjectPolicy:
    with open(file_path, "r", encoding="utf-8") as file:
        payload = json.load(file)

    return parse_audit_project(
        payload=payload,
        active_only=active_only,
    )