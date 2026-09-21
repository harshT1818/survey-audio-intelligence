from pydantic import BaseModel, Field


class DispositionNode(BaseModel):
    id: int | float | str
    text: str
    comments_required: bool = False
    children: list["DispositionNode"] = Field(default_factory=list)


class ValidationPolicy(BaseModel):
    enabled: bool = False
    validation_type: str | None = None
    dispositions: list[DispositionNode] = Field(default_factory=list)


class AuditTagPolicy(BaseModel):
    tag: str
    placeholder: str

    project_code: str

    active: bool
    order: int
    tag_type: str

    question_tag_id: int | None = None

    question_validation: ValidationPolicy
    answer_validation: ValidationPolicy


class AuditProjectPolicy(BaseModel):
    project_code: str
    project_name: str | None = None

    tags: dict[str, AuditTagPolicy] = Field(default_factory=dict)