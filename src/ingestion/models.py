from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class R2SurveyData(BaseModel):
    response_id: str
    project_code: str
    response_time_sec: float | None = None
    answers: dict[str, Any] = Field(default_factory=dict)


class R2TimingData(BaseModel):
    submission_id: str
    raw_tag_times_ms: dict[str, int | None] = Field(
        default_factory=dict
    )


class R2AuditData(BaseModel):
    model_config = ConfigDict(extra="allow")

    response_id: str
    audit_project_code: str
    audit_status: int | None = None
    audit_response: dict[str, Any] = Field(default_factory=dict)


class R2PrivateSample(BaseModel):
    response_id: str
    project_code: str

    survey: R2SurveyData
    timing: R2TimingData
    audit: R2AuditData

    audio_path: Path