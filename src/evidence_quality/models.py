from typing import Literal

from pydantic import BaseModel, Field


EvidenceStatus = Literal[
    "STRONG",
    "MODERATE",
    "WEAK",
    "UNUSABLE",
]


AutomationStatus = Literal[
    "AUTO_FILL_CANDIDATE",
    "PREFILL_CANDIDATE",
    "HUMAN_REVIEW",
    "NO_EVIDENCE",
]


class EvidenceQualityResult(BaseModel):
    raw_text: str

    evidence_status: EvidenceStatus
    automation_status: AutomationStatus

    resolved_option: str | None = None
    resolution_status: str | None = None

    resolution_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    review_required: bool

    reasons: list[str] = Field(
        default_factory=list
    )