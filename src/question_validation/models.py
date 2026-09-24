from pydantic import BaseModel, Field


class QuestionValidationResult(BaseModel):
    expected_question: str
    transcript_text: str

    status: str
    confidence: float = Field(ge=0, le=1)

    matched_text: str | None = None

    review_required: bool
    reason: str