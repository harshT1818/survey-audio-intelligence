from src.audit_engine.models import (
    QuestionAuditResult,
    QuestionEvidence,
    SuggestedDisposition,
)
from src.audit_policy.mapper import (
    map_answer_resolution_to_disposition,
)
from src.audit_policy.models import AuditTagPolicy
from src.domain.models import SurveyQuestion
from src.resolver.models import CanonicalOption
from src.resolver.question_resolver import (
    resolve_question_answer,
)


def audit_question(
    question: SurveyQuestion,
    transcript_text: str,
    canonical_options: list[CanonicalOption],
    tag_policy: AuditTagPolicy,
    start_sec: float | None = None,
    end_sec: float | None = None,
) -> QuestionAuditResult:

    resolution = resolve_question_answer(
        question=question,
        transcript_text=transcript_text,
        canonical_options=canonical_options,
    )

    suggestion = map_answer_resolution_to_disposition(
        resolution=resolution,
        tag_policy=tag_policy,
    )

    return QuestionAuditResult(
        question_key=question.key,
        evidence=QuestionEvidence(
            transcript_text=transcript_text,
            start_sec=start_sec,
            end_sec=end_sec,
        ),
        resolved_option=resolution.resolved_option,
        stored_option=resolution.stored_option,
        resolution_status=resolution.status,
        resolution_confidence=resolution.confidence,
        suggested_disposition=SuggestedDisposition(
            disposition_id=suggestion.disposition_id,
            disposition_text=suggestion.disposition_text,
        ),
        review_required=suggestion.review_required,
        reason=suggestion.reason,
    )