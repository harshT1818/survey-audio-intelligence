from typing import Literal

from pydantic import BaseModel, Field


DialogueRole = Literal[
    "agent",
    "respondent",
    "unknown",
]


EvidenceStrength = Literal[
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


class CorroborationTurn(BaseModel):
    turn_id: str

    role: DialogueRole

    text: str

    upstream_review_required: bool = False

    source_is_mixed: bool = False


class TurnEvidence(BaseModel):
    turn_id: str

    role: DialogueRole

    raw_text: str

    resolved_option: str | None = None

    evidence_status: str | None = None

    automation_status: str | None = None

    resolution_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )


class CorroboratedEvidenceResult(BaseModel):
    resolved_option: str | None = None

    stored_option: str | None = None

    resolution_status: str | None = None

    evidence_strength: EvidenceStrength

    automation_status: AutomationStatus

    direct_support_turn_ids: list[str] = Field(
        default_factory=list
    )

    contextual_support_turn_ids: list[str] = Field(
        default_factory=list
    )

    conflicting_turn_ids: list[str] = Field(
        default_factory=list
    )

    unsafe_turn_ids: list[str] = Field(
        default_factory=list
    )

    turn_evidence: list[TurnEvidence] = Field(
        default_factory=list
    )

    review_required: bool

    reasons: list[str] = Field(
        default_factory=list
    )