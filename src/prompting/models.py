from pydantic import BaseModel, Field


class PromptingEvidence(BaseModel):
    status: str

    confidence: float = Field(
        ge=0,
        le=1,
    )

    agent_followup_text: str
    respondent_text: str

    suggested_option: str | None = None

    review_required: bool

    reason: str