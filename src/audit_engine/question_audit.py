from src.audit_engine.models import (
    QuestionAuditResult,
    QuestionEvidence,
    SuggestedDisposition,
)
from src.audit_policy.mapper import (
    map_answer_resolution_to_disposition,
)
from src.audit_policy.models import AuditTagPolicy
from src.audit_policy.prompting_mapper import (
    map_prompting_answer_disposition,
)
from src.audit_policy.question_mapper import (
    map_question_validation_to_disposition,
)
from src.dialogue.models import QuestionDialogue
from src.dialogue.question_window import (
    extract_question_evidence,
)
from src.domain.models import SurveyQuestion
from src.prompting.rules import detect_prompting
from src.question_validation.fuzzy import (
    validate_question_text,
)
from src.resolver.models import CanonicalOption
from src.resolver.question_resolver import (
    resolve_question_answer,
)


def audit_question(
    question: SurveyQuestion,
    dialogue: QuestionDialogue,
    canonical_options: list[CanonicalOption],
    tag_policy: AuditTagPolicy,
    no_prompting_path: list[str] | None = None,
    prompting_path: list[str] | None = None,
) -> QuestionAuditResult:

    reasons: list[str] = []

    dialogue_evidence = extract_question_evidence(
        dialogue
    )

    reasons.append(
        dialogue_evidence.reason
    )

    question_validation = None
    question_suggestion = None

    answer_resolution = None
    answer_suggestion = None

    prompting = None

    # ---------------------------------------------------------
    # 1. QUESTION VALIDATION
    # ---------------------------------------------------------

    if tag_policy.question_validation.enabled:
        expected_question = (
            question.text_hi
            or question.text_en
            or ""
        )

        question_validation = validate_question_text(
            expected_question=expected_question,
            transcript_text=(
                dialogue_evidence.agent_question_text
            ),
        )

        question_suggestion = (
            map_question_validation_to_disposition(
                validation=question_validation,
                tag_policy=tag_policy,
            )
        )

        reasons.append(
            question_suggestion.reason
        )

    # ---------------------------------------------------------
    # 2. ANSWER RESOLUTION
    #
    # Use the FINAL respondent answer.
    # ---------------------------------------------------------

    if tag_policy.answer_validation.enabled:
        answer_resolution = resolve_question_answer(
            question=question,
            transcript_text=(
                dialogue_evidence.final_respondent_text
            ),
            canonical_options=canonical_options,
        )

        use_prompting_mapping = (
            no_prompting_path is not None
            and prompting_path is not None
        )

        # -----------------------------------------------------
        # 3. PROMPTING DETECTION
        #
        # Prompting is evaluated from the INITIAL respondent
        # answer + agent follow-up.
        # -----------------------------------------------------

        if use_prompting_mapping:
            prompting = detect_prompting(
                respondent_text=(
                    dialogue_evidence.initial_respondent_text
                ),
                agent_followup_text=(
                    dialogue_evidence.agent_followup_text
                ),
                options=canonical_options,
            )

            reasons.append(
                prompting.reason
            )

            answer_suggestion = (
                map_prompting_answer_disposition(
                    resolution=answer_resolution,
                    prompting=prompting,
                    tag_policy=tag_policy,
                    no_prompting_path=no_prompting_path,
                    prompting_path=prompting_path,
                )
            )

        else:
            answer_suggestion = (
                map_answer_resolution_to_disposition(
                    resolution=answer_resolution,
                    tag_policy=tag_policy,
                )
            )

        reasons.append(
            answer_suggestion.reason
        )

    # ---------------------------------------------------------
    # 4. REVIEW DECISION
    # ---------------------------------------------------------

    review_flags = [
        dialogue_evidence.review_required
    ]

    if question_suggestion is not None:
        review_flags.append(
            question_suggestion.review_required
        )

    if prompting is not None:
        review_flags.append(
            prompting.review_required
        )

    if answer_suggestion is not None:
        review_flags.append(
            answer_suggestion.review_required
        )

    review_required = any(
        review_flags
    )

    # ---------------------------------------------------------
    # 5. FINAL RESULT
    # ---------------------------------------------------------

    return QuestionAuditResult(
        question_key=question.key,

        evidence=QuestionEvidence(
            agent_text=(
                dialogue_evidence.agent_question_text
            ),
            respondent_text=(
                dialogue_evidence.final_respondent_text
            ),
            agent_followup_text=(
                dialogue_evidence.agent_followup_text
            ),
            start_sec=(
                dialogue_evidence.start_sec
            ),
            end_sec=(
                dialogue_evidence.end_sec
            ),
        ),

        question_validation_status=(
            question_validation.status
            if question_validation
            else None
        ),

        question_validation_confidence=(
            question_validation.confidence
            if question_validation
            else None
        ),

        question_disposition=(
            SuggestedDisposition(
                disposition_id=(
                    question_suggestion.disposition_id
                ),
                disposition_text=(
                    question_suggestion.disposition_text
                ),
            )
            if question_suggestion
            else None
        ),

        resolved_option=(
            answer_resolution.resolved_option
            if answer_resolution
            else None
        ),

        stored_option=(
            answer_resolution.stored_option
            if answer_resolution
            else None
        ),

        answer_resolution_status=(
            answer_resolution.status
            if answer_resolution
            else None
        ),

        answer_resolution_confidence=(
            answer_resolution.confidence
            if answer_resolution
            else None
        ),

        prompting_status=(
            prompting.status
            if prompting
            else None
        ),

        prompting_confidence=(
            prompting.confidence
            if prompting
            else None
        ),

        prompted_option=(
            prompting.suggested_option
            if prompting
            else None
        ),

        answer_disposition=(
            SuggestedDisposition(
                disposition_id=(
                    answer_suggestion.disposition_id
                ),
                disposition_text=(
                    answer_suggestion.disposition_text
                ),
                disposition_path=(
                    getattr(
                        answer_suggestion,
                        "disposition_path",
                        [],
                    )
                ),
            )
            if answer_suggestion
            else None
        ),

        review_required=review_required,

        reasons=reasons,
    )