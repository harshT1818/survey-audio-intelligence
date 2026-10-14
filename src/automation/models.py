from typing import Literal

from pydantic import BaseModel, Field

from src.audit_engine.models import (
    SuggestedDisposition,
)


AutomationAction = Literal[
    "AUTO_FILL",
    "PREFILL",
    "HUMAN_REVIEW",
]


DispositionSide = Literal[
    "question",
    "answer",
]


ProposalAction = Literal[
    "AUTO_FILL",
    "PREFILL",
]


class DispositionProposal(BaseModel):
    side: DispositionSide

    disposition: SuggestedDisposition

    action: ProposalAction

    reason: str


class QuestionAutomationDecision(BaseModel):
    question_key: str

    action: AutomationAction

    proposals: list[
        DispositionProposal
    ] = Field(
        default_factory=list
    )

    unresolved_sides: list[
        DispositionSide
    ] = Field(
        default_factory=list
    )

    review_required: bool

    reasons: list[str] = Field(
        default_factory=list
    )