from pydantic import BaseModel, Field


class CanonicalOption(BaseModel):
    value: str
    labels: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


class ResolutionCandidate(BaseModel):
    option: str
    matched_text: str
    score: float = Field(ge=0, le=1)


class AnswerResolution(BaseModel):
    raw_text: str

    resolved_option: str | None = None
    stored_option: str | None = None

    status: str
    confidence: float = Field(ge=0, le=1)

    candidates: list[ResolutionCandidate] = Field(
        default_factory=list
    )