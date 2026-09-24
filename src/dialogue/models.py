from typing import Literal

from pydantic import BaseModel, Field, model_validator


SpeakerRole = Literal[
    "agent",
    "respondent",
    "unknown",
]


class SpeechTurn(BaseModel):
    speaker: SpeakerRole
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
        ) != (
            self.end_sec is None
        ):
            raise ValueError(
                "start_sec and end_sec must either "
                "both be provided or both be null"
            )

        if (
            self.start_sec is not None
            and self.end_sec is not None
            and self.end_sec <= self.start_sec
        ):
            raise ValueError(
                "end_sec must be greater than start_sec"
            )

        return self


class QuestionDialogue(BaseModel):
    turns: list[SpeechTurn] = Field(
        default_factory=list
    )


class QuestionDialogueEvidence(BaseModel):
    agent_question_text: str

    initial_respondent_text: str

    agent_followup_text: str

    final_respondent_text: str

    start_sec: float | None = None
    end_sec: float | None = None

    review_required: bool = False

    reason: str = ""