from typing import Any

from pydantic import BaseModel, Field

from src.dialogue.models import SpeechTurn
from src.resolver.models import CanonicalOption


class ExpectedAuditResult(BaseModel):
    question_validation_status: str | None = None
    answer_resolution_status: str | None = None
    resolved_option: str | None = None
    prompting_status: str | None = None
    answer_disposition_text: str | None = None
    review_required: bool


class EvaluationCase(BaseModel):
    case_id: str
    description: str

    question_key: str
    question_text_hi: str
    question_type: str = "single_choice"

    stored_answer: str

    options: list[CanonicalOption]

    turns: list[SpeechTurn]

    prompting_aware: bool = False

    no_prompting_path: list[str] | None = None
    prompting_path: list[str] | None = None

    expected: ExpectedAuditResult


class EvaluationFixture(BaseModel):
    fixture_name: str

    cases: list[EvaluationCase] = Field(
        default_factory=list
    )


class EvaluationCaseResult(BaseModel):
    case_id: str
    passed: bool

    expected: ExpectedAuditResult

    actual: dict[str, Any]

    failures: list[str] = Field(
        default_factory=list
    )


class EvaluationSummary(BaseModel):
    fixture_name: str

    total_cases: int
    passed_cases: int
    failed_cases: int

    results: list[EvaluationCaseResult]