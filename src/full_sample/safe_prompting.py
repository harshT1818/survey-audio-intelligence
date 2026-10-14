from typing import Any

from src.full_sample.prompting_benchmark import (
    select_question_anchor,
)
from src.full_sample.turn_safety import (
    decision_rejection_reasons,
    safe_turns_after,
    select_first_safe_turn_after,
)
from src.prompting.rules import (
    detect_prompting,
)
from src.resolver.models import (
    CanonicalOption,
)


def _base_result(
    prediction: str,
    review_required: bool,
    reason: str,
    *,
    detector_result: Any = None,
    raw_detector_prediction: (
        str
        | None
    ) = None,
    anchor_agent_turn: Any = None,
    initial_respondent_turn: Any = None,
    agent_followup_turns: (
        list[dict[str, Any]]
        | None
    ) = None,
    rejected_respondent_turns: (
        list[dict[str, Any]]
        | None
    ) = None,
    rejected_agent_followup_turns: (
        list[dict[str, Any]]
        | None
    ) = None,
    anchor_similarity: (
        float
        | None
    ) = None,
    anchor_method: (
        str
        | None
    ) = None,
    anchor_candidates: (
        list[dict[str, Any]]
        | None
    ) = None,
    decision_safe: bool = False,
) -> dict[str, Any]:
    return {
        "prediction": prediction,
        "raw_detector_prediction": (
            raw_detector_prediction
        ),
        "review_required": (
            review_required
        ),
        "reason": reason,
        "detector_result": (
            detector_result
        ),
        "anchor_agent_turn": (
            anchor_agent_turn
        ),
        "initial_respondent_turn": (
            initial_respondent_turn
        ),
        "agent_followup_turns": (
            agent_followup_turns
            or []
        ),
        "rejected_respondent_turns": (
            rejected_respondent_turns
            or []
        ),
        "rejected_agent_followup_turns": (
            rejected_agent_followup_turns
            or []
        ),
        "anchor_similarity": (
            anchor_similarity
        ),
        "anchor_method": (
            anchor_method
        ),
        "anchor_candidates": (
            anchor_candidates
            or []
        ),
        "decision_safe": (
            decision_safe
        ),
    }


def _detector_prediction(
    status: str,
) -> str:
    if (
        status
        == "PROMPTING_EVIDENCE"
    ):
        return "PROMPTING"

    if (
        status
        == "NO_PROMPTING_EVIDENCE"
    ):
        return "NO_PROMPTING"

    return "UNCERTAIN"


def evaluate_prompting_dialogue_safe(
    dialogue: dict[str, Any],
    question_window: dict[str, Any],
    options: list[
        CanonicalOption
    ],
) -> dict[str, Any]:
    """
    Safety-aware version of prompting evaluation.

    Differences from the current benchmark adapter:

    1. Question anchor still comes from SurveyXpress
       question-text similarity.

    2. A turn with known raw cross-speaker overlap is
       never treated as clean decision evidence.

    3. If the first respondent turn is unsafe, we keep
       its rejection in the trace and look for the next
       safe respondent turn.

    4. Unsafe agent follow-ups are also excluded.

    5. If any evidence inside the decision sequence had
       to be rejected, a resolved detector result is
       downgraded to UNCERTAIN rather than silently
       automating around missing evidence.
    """
    if (
        dialogue.get(
            "evidence_status"
        )
        != "ROLE_DIALOGUE_AVAILABLE"
    ):
        return _base_result(
            prediction=(
                "INSUFFICIENT_ROLE_EVIDENCE"
            ),
            review_required=True,
            reason=(
                "Both usable agent and respondent "
                "speech were not available."
            ),
            decision_safe=False,
        )

    turns = dialogue.get(
        "turns",
        [],
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
        anchor_result[
            "turn"
        ]
    )

    if anchor is None:
        return _base_result(
            prediction=(
                "INSUFFICIENT_ROLE_EVIDENCE"
            ),
            review_required=True,
            reason=(
                "No safe SurveyXpress question "
                "anchor was available."
            ),
            anchor_similarity=(
                anchor_result.get(
                    "score"
                )
            ),
            anchor_method=(
                anchor_result.get(
                    "method"
                )
            ),
            anchor_candidates=(
                anchor_result.get(
                    "candidates",
                    [],
                )
            ),
            decision_safe=False,
        )

    anchor_reasons = (
        decision_rejection_reasons(
            anchor
        )
    )

    if anchor_reasons:
        return _base_result(
            prediction=(
                "INSUFFICIENT_ROLE_EVIDENCE"
            ),
            review_required=True,
            reason=(
                "The matched SurveyXpress "
                "question anchor is contaminated "
                "and cannot safely start the "
                "prompting decision sequence."
            ),
            anchor_agent_turn=(
                anchor
            ),
            anchor_similarity=(
                anchor_result.get(
                    "score"
                )
            ),
            anchor_method=(
                anchor_result.get(
                    "method"
                )
            ),
            anchor_candidates=(
                anchor_result.get(
                    "candidates",
                    [],
                )
            ),
            decision_safe=False,
        )

    anchor_end = float(
        anchor[
            "end_sec"
        ]
    )

    respondent_selection = (
        select_first_safe_turn_after(
            turns=turns,
            start_sec=anchor_end,
            role="respondent",
            tolerance_sec=0.15,
        )
    )

    respondent = (
        respondent_selection[
            "turn"
        ]
    )

    rejected_respondents = (
        respondent_selection[
            "rejected"
        ]
    )

    if respondent is None:
        return _base_result(
            prediction=(
                "INSUFFICIENT_ROLE_EVIDENCE"
            ),
            review_required=True,
            reason=(
                "No decision-safe respondent "
                "speech was recovered after the "
                "matched agent question turn."
            ),
            anchor_agent_turn=(
                anchor
            ),
            rejected_respondent_turns=(
                rejected_respondents
            ),
            anchor_similarity=(
                anchor_result.get(
                    "score"
                )
            ),
            anchor_method=(
                anchor_result.get(
                    "method"
                )
            ),
            anchor_candidates=(
                anchor_result.get(
                    "candidates",
                    [],
                )
            ),
            decision_safe=False,
        )

    respondent_end = float(
        respondent[
            "end_sec"
        ]
    )

    followup_selection = (
        safe_turns_after(
            turns=turns,
            start_sec=respondent_end,
            role="agent",
            tolerance_sec=0.15,
        )
    )

    safe_followups = (
        followup_selection[
            "accepted"
        ]
    )

    rejected_followups = (
        followup_selection[
            "rejected"
        ]
    )

    respondent_text = str(
        respondent.get(
            "transcript",
            "",
        )
    )

    agent_followup_text = " ".join(
        str(
            turn.get(
                "transcript",
                "",
            )
        )
        for turn in safe_followups
        if str(
            turn.get(
                "transcript",
                "",
            )
        ).strip()
    )

    detector = detect_prompting(
        respondent_text=(
            respondent_text
        ),
        agent_followup_text=(
            agent_followup_text
        ),
        options=options,
    )

    raw_prediction = (
        _detector_prediction(
            detector.status
        )
    )

    rejected_decision_evidence = bool(
        rejected_respondents
        or rejected_followups
    )

    if (
        raw_prediction
        in {
            "PROMPTING",
            "NO_PROMPTING",
        }
        and rejected_decision_evidence
    ):
        prediction = "UNCERTAIN"

        reason = (
            "The prompting detector produced "
            f"{raw_prediction}, but one or more "
            "post-anchor turns were excluded "
            "because they contained unsafe "
            "speaker evidence. Automatic "
            "classification is withheld."
        )

        review_required = True
        decision_safe = False

    else:
        prediction = (
            raw_prediction
        )

        reason = detector.reason

        review_required = (
            detector.review_required
        )

        decision_safe = (
            not rejected_decision_evidence
            and prediction
            in {
                "PROMPTING",
                "NO_PROMPTING",
            }
        )

    return _base_result(
        prediction=prediction,
        raw_detector_prediction=(
            raw_prediction
        ),
        review_required=(
            review_required
        ),
        reason=reason,
        detector_result=(
            detector.model_dump()
        ),
        anchor_agent_turn=(
            anchor
        ),
        initial_respondent_turn=(
            respondent
        ),
        agent_followup_turns=(
            safe_followups
        ),
        rejected_respondent_turns=(
            rejected_respondents
        ),
        rejected_agent_followup_turns=(
            rejected_followups
        ),
        anchor_similarity=(
            anchor_result.get(
                "score"
            )
        ),
        anchor_method=(
            anchor_result.get(
                "method"
            )
        ),
        anchor_candidates=(
            anchor_result.get(
                "candidates",
                [],
            )
        ),
        decision_safe=(
            decision_safe
        ),
    )