from pydantic import BaseModel, Field, model_validator


class DiarizationSegment(BaseModel):
    speaker_id: str

    start_sec: float = Field(
        ge=0,
    )

    end_sec: float = Field(
        gt=0,
    )

    @model_validator(mode="after")
    def validate_timing(self):
        if self.end_sec <= self.start_sec:
            raise ValueError(
                "end_sec must be greater than start_sec"
            )

        return self


class DiarizationResult(BaseModel):
    audio_id: str
    model_name: str

    segments: list[DiarizationSegment] = Field(
        default_factory=list
    )