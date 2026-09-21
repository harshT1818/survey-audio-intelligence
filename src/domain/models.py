from typing import Any

from pydantic import BaseModel, Field, model_validator


class SurveyQuestion(BaseModel):
    key: str = Field(min_length=1)

    text_hi: str | None = None
    text_en: str | None = None

    type: str = Field(min_length=1)

    # Keeping these flexible for now because future SurveyXpress
    # questions may have more complex option structures.
    options: list[Any] = Field(default_factory=list)

    selected_answer: Any = None

    # Timing remains optional until we confirm the exact timing semantics.
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_timing(self):
        # For now, either both timings should exist or neither should.
        if (self.start_ms is None) != (self.end_ms is None):
            raise ValueError(
                "start_ms and end_ms must either both be provided or both be null"
            )

        if (
            self.start_ms is not None
            and self.end_ms is not None
            and self.end_ms <= self.start_ms
        ):
            raise ValueError("end_ms must be greater than start_ms")

        return self


class SurveyAuditRequest(BaseModel):
    response_id: str = Field(min_length=1)
    project_code: str = Field(min_length=1)

    language: str = "hi"

    # Local file path for experiments now.
    # Later this can also be an S3/HTTP URL.
    audio_source: str = Field(min_length=1)

    questions: list[SurveyQuestion] = Field(min_length=1)

    # Flexible project/sample context such as:
    # state, AC, survey round, etc.
    context: dict[str, Any] = Field(default_factory=dict)