from typing import Any

from pydantic import BaseModel, Field

from src.audit_engine.models import (
    QuestionAuditResult,
)
from src.audit_engine.question_audit import (
    audit_question,
)
from src.audit_policy.models import (
    AuditTagPolicy,
)
from src.automation.decision import (
    decide_question_automation,
)
from src.automation.models import (
    QuestionAutomationDecision,
)
from src.dialogue.models import (
    QuestionDialogue,
    SpeechTurn,
)
from src.domain.models import (
    SurveyQuestion,
)
from src.evidence_quality.corroboration import (
    corroborate_answer_evidence,
)
from src.evidence_quality.corroboration_models import (
    CorroboratedEvidenceResult,
    CorroborationTurn,
)
from src.full_sample.prompting_benchmark import (
    select_question_anchor,
)
from src.full_sample.turn_safety import (
    decision_rejection_reasons,
)
from src.resolver.models import (
    CanonicalOption,
)


class RejectedAuditTurn(BaseModel):
    turn_id: str

    role: str

    start_sec: float | None = None
    end_sec: float | None = None

    text: str

    reasons: list[str] = Field(
        default_factory=list
    )

    material_for_review: bool


class SafeAuditTrace(BaseModel):
    anchor_found: bool = False

    anchor_turn_id: str | None = None
    anchor_method: str | None = None
    anchor_similarity: float | None = None

    input_turn_count: int = 0

    pre_anchor_turn_count: int = 0
    post_anchor_turn_count: int = 0

    safe_audit_turn_count: int = 0
    corroboration_turn_count: int = 0

    rejected_turns: list[
        RejectedAuditTurn
    ] = Field(
        default_factory=list
    )

    ignored_short_turn_ids: list[
        str
    ] = Field(
        default_factory=list
    )

    review_required: bool = False

    reasons: list[str] = Field(
        default_factory=list
    )


class SafeAuditInputs(BaseModel):
    dialogue: QuestionDialogue

    corroboration_turns: list[
        CorroborationTurn
    ] = Field(
        default_factory=list
    )

    trace: SafeAuditTrace


class FullQuestionAuditResult(BaseModel):
    audit: QuestionAuditResult

    corroboration: (
        CorroboratedEvidenceResult
    )

    automation: (
        QuestionAutomationDecision
    )

    trace: SafeAuditTrace


def _normalize_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value).split()
    )


def _turn_start(
    turn: dict[str, Any],
) -> float | None:
    value = turn.get(
        "start_sec"
    )

    if value is None:
        return None

    return float(value)


def _turn_end(
    turn: dict[str, Any],
) -> float | None:
    value = turn.get(
        "end_sec"
    )

    if value is None:
        return None

    return float(value)


def _turn_duration(
    turn: dict[str, Any],
) -> float:
    start = _turn_start(
        turn
    )

    end = _turn_end(
        turn
    )

    if (
        start is None
        or end is None
    ):
        return 0.0

    return max(
        0.0,
        end - start,
    )


def _turn_id(
    tag: str,
    turn: dict[str, Any],
    fallback_index: int,
) -> str:
    turn_index = turn.get(
        "turn_index"
    )

    if turn_index is None:
        turn_index = (
            fallback_index
        )

    return (
        f"{tag}:turn:"
        f"{turn_index}"
    )


def _same_turn(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    left_index = left.get(
        "turn_index"
    )

    right_index = right.get(
        "turn_index"
    )

    if (
        left_index is not None
        and right_index is not None
    ):
        return (
            left_index
            == right_index
        )

    left_start = _turn_start(
        left
    )

    right_start = _turn_start(
        right
    )

    left_end = _turn_end(
        left
    )

    right_end = _turn_end(
        right
    )

    if (
        left_start is None
        or right_start is None
        or left_end is None
        or right_end is None
    ):
        return (
            left.get("role")
            == right.get("role")
            and _normalize_text(
                left.get(
                    "transcript"
                )
            )
            == _normalize_text(
                right.get(
                    "transcript"
                )
            )
        )

    return (
        left.get("role")
        == right.get("role")
        and abs(
            left_start
            - right_start
        )
        < 0.001
        and abs(
            left_end
            - right_end
        )
        < 0.001
        and _normalize_text(
            left.get(
                "transcript"
            )
        )
        == _normalize_text(
            right.get(
                "transcript"
            )
        )
    )


def _is_mixed_source(
    turn: dict[str, Any],
) -> bool:
    return bool(
        turn.get(
            "raw_cross_speaker_overlap",
            False,
        )
        or turn.get(
            "cross_speaker_overlap",
            False,
        )
    )


def _is_material_rejection(
    turn: dict[str, Any],
    reasons: list[str],
    material_missing_audio_min_sec: float,
) -> bool:
    material_reason_names = {
        "RAW_CROSS_SPEAKER_OVERLAP",
        "CROSS_SPEAKER_OVERLAP",
        "UNKNOWN_ROLE",
    }

    if any(
        reason
        in material_reason_names
        for reason in reasons
    ):
        return True

    asr_status = str(
        turn.get(
            "asr_status",
            "",
        )
    )

    if asr_status == "MISSING":
        return True

    duration = _turn_duration(
        turn
    )

    if (
        asr_status
        in {
            "EMPTY",
            "ERROR",
            "FAILED",
        }
        and duration
        >= material_missing_audio_min_sec
    ):
        return True

    if (
        "ASR_NOT_COMPLETE"
        in reasons
        and asr_status
        != "SKIPPED_SHORT"
        and duration
        >= material_missing_audio_min_sec
    ):
        return True

    return False


def _sorted_turns(
    dialogue: dict[str, Any],
) -> list[dict[str, Any]]:
    turns = list(
        dialogue.get(
            "turns",
            [],
        )
    )

    def sort_key(
        item: dict[str, Any],
    ) -> tuple[
        float,
        float,
        int,
    ]:
        start = _turn_start(
            item
        )

        end = _turn_end(
            item
        )

        return (
            (
                start
                if start is not None
                else float("inf")
            ),
            (
                end
                if end is not None
                else float("inf")
            ),
            int(
                item.get(
                    "turn_index",
                    0,
                )
                or 0
            ),
        )

    turns.sort(
        key=sort_key
    )

    return turns


def build_safe_audit_inputs(
    dialogue: dict[str, Any],
    question_window: dict[str, Any],
    material_missing_audio_min_sec: float = 0.35,
) -> SafeAuditInputs:
    """
    Convert rich full-sample dialogue into the two inputs
    needed by the existing audit stack:

    1. QuestionDialogue containing only safe turns.
    2. CorroborationTurn objects preserving meaningful
       unsafe context for automation gating.

    Evidence before the matched SurveyXpress question
    anchor is intentionally excluded.
    """
    tag = str(
        dialogue.get(
            "tag",
            "",
        )
    )

    turns = _sorted_turns(
        dialogue
    )

    trace = SafeAuditTrace(
        input_turn_count=len(
            turns
        )
    )

    anchor_result = (
        select_question_anchor(
            dialogue=dialogue,
            question_window=(
                question_window
            ),
        )
    )

    anchor = (
        anchor_result.get(
            "turn"
        )
    )

    trace.anchor_method = (
        anchor_result.get(
            "method"
        )
    )

    trace.anchor_similarity = (
        anchor_result.get(
            "score"
        )
    )

    if anchor is None:
        trace.review_required = True

        trace.reasons.append(
            (
                "No reliable SurveyXpress "
                "question anchor was found."
            )
        )

        return SafeAuditInputs(
            dialogue=(
                QuestionDialogue(
                    turns=[]
                )
            ),
            corroboration_turns=[],
            trace=trace,
        )

    trace.anchor_found = True

    anchor_position = None

    for index, turn in enumerate(
        turns
    ):
        if _same_turn(
            turn,
            anchor,
        ):
            anchor_position = index
            break

    if anchor_position is None:
        trace.review_required = True

        trace.reasons.append(
            (
                "The selected question anchor "
                "could not be mapped back to "
                "the dialogue turn sequence."
            )
        )

        return SafeAuditInputs(
            dialogue=(
                QuestionDialogue(
                    turns=[]
                )
            ),
            corroboration_turns=[],
            trace=trace,
        )

    trace.pre_anchor_turn_count = (
        anchor_position
    )

    local_turns = turns[
        anchor_position:
    ]

    trace.post_anchor_turn_count = (
        len(
            local_turns
        )
    )

    safe_speech_turns = []

    corroboration_turns = []

    for local_index, turn in enumerate(
        local_turns
    ):
        absolute_index = (
            anchor_position
            + local_index
        )

        turn_id = _turn_id(
            tag=tag,
            turn=turn,
            fallback_index=(
                absolute_index
            ),
        )

        if local_index == 0:
            trace.anchor_turn_id = (
                turn_id
            )

        text = _normalize_text(
            turn.get(
                "transcript",
                "",
            )
        )

        role = str(
            turn.get(
                "role",
                "unknown",
            )
        )

        if role not in {
            "agent",
            "respondent",
            "unknown",
        }:
            role = "unknown"

        reasons = (
            decision_rejection_reasons(
                turn
            )
        )

        material_rejection = (
            _is_material_rejection(
                turn=turn,
                reasons=reasons,
                material_missing_audio_min_sec=(
                    material_missing_audio_min_sec
                ),
            )
        )

        if reasons:
            trace.rejected_turns.append(
                RejectedAuditTurn(
                    turn_id=turn_id,
                    role=role,
                    start_sec=(
                        _turn_start(
                            turn
                        )
                    ),
                    end_sec=(
                        _turn_end(
                            turn
                        )
                    ),
                    text=text,
                    reasons=reasons,
                    material_for_review=(
                        material_rejection
                    ),
                )
            )

            if (
                turn.get(
                    "asr_status"
                )
                == "SKIPPED_SHORT"
                and not material_rejection
            ):
                trace.ignored_short_turn_ids.append(
                    turn_id
                )

        else:
            safe_speech_turns.append(
                SpeechTurn(
                    speaker=role,
                    text=text,
                    start_sec=(
                        _turn_start(
                            turn
                        )
                    ),
                    end_sec=(
                        _turn_end(
                            turn
                        )
                    ),
                )
            )

        if (
            not reasons
            or material_rejection
        ):
            corroboration_turns.append(
                CorroborationTurn(
                    turn_id=turn_id,
                    role=role,
                    text=text,
                    upstream_review_required=(
                        material_rejection
                    ),
                    source_is_mixed=(
                        _is_mixed_source(
                            turn
                        )
                    ),
                )
            )

    anchor_reasons = (
        decision_rejection_reasons(
            anchor
        )
    )

    if anchor_reasons:
        trace.review_required = True

        trace.reasons.append(
            (
                "The matched question anchor "
                "contains unsafe upstream "
                "speaker or ASR evidence."
            )
        )

        safe_speech_turns = []

    material_rejected_turns = [
        item
        for item
        in trace.rejected_turns
        if item.material_for_review
    ]

    if material_rejected_turns:
        trace.review_required = True

        trace.reasons.append(
            (
                "One or more decision-local "
                "turns contain material unsafe "
                "speaker or ASR evidence."
            )
        )

    trace.safe_audit_turn_count = (
        len(
            safe_speech_turns
        )
    )

    trace.corroboration_turn_count = (
        len(
            corroboration_turns
        )
    )

    return SafeAuditInputs(
        dialogue=QuestionDialogue(
            turns=safe_speech_turns
        ),
        corroboration_turns=(
            corroboration_turns
        ),
        trace=trace,
    )


def run_full_question_audit(
    question: SurveyQuestion,
    rich_dialogue: dict[str, Any],
    question_window: dict[str, Any],
    canonical_options: list[
        CanonicalOption
    ],
    tag_policy: AuditTagPolicy,
    no_prompting_path: (
        list[str]
        | None
    ) = None,
    prompting_path: (
        list[str]
        | None
    ) = None,
    require_question_disposition: bool = True,
    require_answer_disposition: bool = True,
) -> FullQuestionAuditResult:
    inputs = build_safe_audit_inputs(
        dialogue=rich_dialogue,
        question_window=(
            question_window
        ),
    )

    audit = audit_question(
        question=question,
        dialogue=inputs.dialogue,
        canonical_options=(
            canonical_options
        ),
        tag_policy=tag_policy,
        no_prompting_path=(
            no_prompting_path
        ),
        prompting_path=(
            prompting_path
        ),
        prompting_evidence_complete=not any(
            item.material_for_review
            for item in inputs.trace.rejected_turns
        ),
    )

    corroboration = (
        corroborate_answer_evidence(
            turns=(
                inputs.corroboration_turns
            ),
            options=canonical_options,
            stored_option=(
                audit.stored_option
            ),
        )
    )

    automation = (
        decide_question_automation(
            audit=audit,
            evidence=corroboration,
            require_question_disposition=(
                require_question_disposition
            ),
            require_answer_disposition=(
                require_answer_disposition
            ),
        )
    )

    #
    # The existing audit engine knows nothing about
    # full-sample provenance. If the adapter found
    # material unsafe context, do not permit the final
    # bundle to silently appear fully review-free.
    #
    if (
        inputs.trace.review_required
        and automation.action
        == "AUTO_FILL"
    ):
        automation = (
            QuestionAutomationDecision(
                question_key=(
                    automation.question_key
                ),
                action="PREFILL",
                proposals=[
                    proposal.model_copy(
                        update={
                            "action": (
                                "PREFILL"
                            )
                        }
                    )
                    for proposal
                    in automation.proposals
                ],
                unresolved_sides=(
                    automation.unresolved_sides
                ),
                review_required=True,
                reasons=[
                    *automation.reasons,
                    (
                        "Full-sample adapter found "
                        "material unsafe upstream "
                        "evidence, so AUTO_FILL "
                        "was downgraded to PREFILL."
                    ),
                ],
            )
        )

    #
    # Overlapping question windows (the interviewer moved
    # back and forth between questions) can hold another
    # question's answer, so answer evidence here cannot be
    # attributed safely. The question side is unaffected.
    #
    if question_window.get(
        "overlap_review_required"
    ):
        automation = (
            withhold_answer_proposals(
                automation,
                OVERLAPPING_WINDOW_REASON,
            )
        )

    return FullQuestionAuditResult(
        audit=audit,
        corroboration=(
            corroboration
        ),
        automation=automation,
        trace=inputs.trace,
    )


OVERLAPPING_WINDOW_REASON = (
    "Question window overlaps another question's "
    "window, so answer evidence may belong to the "
    "other question; answer proposals were withheld."
)


def withhold_answer_proposals(
    automation: QuestionAutomationDecision,
    reason: str,
) -> QuestionAutomationDecision:
    proposals = [
        proposal
        for proposal in automation.proposals
        if proposal.side != "answer"
    ]

    unresolved = list(
        automation.unresolved_sides
    )

    if "answer" not in unresolved:
        unresolved.append("answer")

    return QuestionAutomationDecision(
        question_key=automation.question_key,
        action=(
            "PREFILL"
            if proposals
            else "HUMAN_REVIEW"
        ),
        proposals=[
            proposal.model_copy(
                update={"action": "PREFILL"}
            )
            for proposal in proposals
        ],
        unresolved_sides=unresolved,
        review_required=True,
        reasons=[
            *automation.reasons,
            reason,
        ],
    )