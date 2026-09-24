from pydantic import BaseModel, Field


class QuestionEvidence(BaseModel):
    transcript_text: str
    start_sec: float | None = None
    end_sec: float | None = None


class SuggestedDisposition(BaseModel):
    disposition_id: int | float | str | None = None
    disposition_text: str | None = None


class QuestionAuditResult(BaseModel):
    question_key: str

    evidence: QuestionEvidence

    resolved_option: str | None = None
    stored_option: str | None = None

    resolution_status: str
    resolution_confidence: float = Field(
        ge=0,
        le=1,
    )

    suggested_disposition: SuggestedDisposition

    review_required: bool
    reason: str