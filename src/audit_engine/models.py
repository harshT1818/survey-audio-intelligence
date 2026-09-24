from pydantic import BaseModel, Field


class QuestionEvidence(BaseModel):
    agent_text: str
    respondent_text: str
    agent_followup_text: str = ""

    start_sec: float | None = None
    end_sec: float | None = None


class SuggestedDisposition(BaseModel):
    disposition_id: int | float | str | None = None
    disposition_text: str | None = None
    disposition_path: list[str] = Field(
        default_factory=list
    )


class QuestionAuditResult(BaseModel):
    question_key: str

    evidence: QuestionEvidence

    question_validation_status: str | None = None
    question_validation_confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    question_disposition: SuggestedDisposition | None = None

    resolved_option: str | None = None
    stored_option: str | None = None

    answer_resolution_status: str | None = None
    answer_resolution_confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    prompting_status: str | None = None
    prompting_confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    prompted_option: str | None = None

    answer_disposition: SuggestedDisposition | None = None

    review_required: bool

    reasons: list[str] = Field(
        default_factory=list
    )