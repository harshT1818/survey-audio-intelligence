from typing import Literal

from pydantic import BaseModel, Field, model_validator


SpeakerRole = Literal[
    "agent",
    "respondent",
    "unknown",
]


class RawSpeakerTurn(BaseModel):
    segment_id: str
    speaker_id: str
    text: str

    start_sec: float | None = Field(
        default=None,
        ge=0,
    )

    end_sec: float | None = Field(
        default=None,
        ge=0,
    )

    @model_validator(mode="after")
    def validate_timing(self):
        if (
            self.start_sec is None
            and self.end_sec is None
        ):
            return self

        if (
            self.start_sec is None
            or self.end_sec is None
        ):
            raise ValueError(
                "start_sec and end_sec must both "
                "be provided or both be null"
            )

        if self.end_sec <= self.start_sec:
            raise ValueError(
                "end_sec must be greater than start_sec"
            )

        return self


class InferredSpeakerTurn(BaseModel):
    segment_id: str
    speaker_id: str
    text: str

    role: SpeakerRole

    role_score: float = Field(
        ge=0,
        le=1,
    )

    start_sec: float | None = None
    end_sec: float | None = None

    review_required: bool = False

    reasons: list[str] = Field(
        default_factory=list
    )


class SpeakerRoleInferenceResult(BaseModel):
    turns: list[InferredSpeakerTurn] = Field(
        default_factory=list
    )

    dominant_agent_speaker_id: str | None = None
    dominant_respondent_speaker_id: str | None = None