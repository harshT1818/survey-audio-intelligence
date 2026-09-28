from src.audit_engine.models import (
    QuestionAuditResult,
)
from src.automation.models import (
    DispositionProposal,
    QuestionAutomationDecision,
)
from src.evidence_quality.corroboration_models import (
    CorroboratedEvidenceResult,
)


def _question_proposal(
    audit: QuestionAuditResult,
) -> DispositionProposal | None:

    if (
        audit.question_validation_status
        != "ASKED_RIGHT"
    ):
        return None

    if audit.question_disposition is None:
        return None

    if (
        audit.question_disposition
        .disposition_id
        is None
    ):
        return None

    return DispositionProposal(
        side="question",
        disposition=(
            audit.question_disposition
        ),
        action="AUTO_FILL",
        reason=(
            "Question was confidently matched "
            "and has an exact configured "
            "Audit CRM disposition."
        ),
    )


def _answer_options_agree(
    audit: QuestionAuditResult,
    evidence: CorroboratedEvidenceResult,
) -> bool:

    if (
        audit.resolved_option is None
        or evidence.resolved_option is None
    ):
        return True

    return (
        audit.resolved_option.strip().lower()
        ==
        evidence.resolved_option.strip().lower()
    )


def _answer_proposal(
    audit: QuestionAuditResult,
    evidence: CorroboratedEvidenceResult,
) -> DispositionProposal | None:

    if audit.answer_disposition is None:
        return None

    if (
        audit.answer_disposition
        .disposition_id
        is None
    ):
        return None

    if not _answer_options_agree(
        audit,
        evidence,
    ):
        return None

    if (
        evidence.automation_status
        == "AUTO_FILL_CANDIDATE"
    ):
        if (
            evidence.review_required
            or audit.prompting_status
            == "UNCERTAIN"
        ):
            return DispositionProposal(
                side="answer",
                disposition=(
                    audit.answer_disposition
                ),
                action="PREFILL",
                reason=(
                    "Answer disposition exists, "
                    "but supporting context still "
                    "requires review."
                ),
            )

        return DispositionProposal(
            side="answer",
            disposition=(
                audit.answer_disposition
            ),
            action="AUTO_FILL",
            reason=(
                "Corroborated respondent evidence "
                "supports the exact configured "
                "answer disposition."
            ),
        )

    if (
        evidence.automation_status
        == "PREFILL_CANDIDATE"
    ):
        return DispositionProposal(
            side="answer",
            disposition=(
                audit.answer_disposition
            ),
            action="PREFILL",
            reason=(
                "Answer evidence is useful enough "
                "to prefill but still requires "
                "human confirmation."
            ),
        )

    return None


def decide_question_automation(
    audit: QuestionAuditResult,
    evidence: CorroboratedEvidenceResult,
    require_question_disposition: bool = True,
    require_answer_disposition: bool = True,
) -> QuestionAutomationDecision:

    proposals = []

    reasons = []

    question = _question_proposal(
        audit
    )

    if question is not None:
        proposals.append(
            question
        )

    answer = _answer_proposal(
        audit,
        evidence,
    )

    if answer is not None:
        proposals.append(
            answer
        )

    unresolved_sides = []

    if (
        require_question_disposition
        and question is None
    ):
        unresolved_sides.append(
            "question"
        )

    if (
        require_answer_disposition
        and answer is None
    ):
        unresolved_sides.append(
            "answer"
        )

    if not _answer_options_agree(
        audit,
        evidence,
    ):
        reasons.append(
            (
                "Question audit and corroborated "
                "evidence resolved different "
                "answer options."
            )
        )

    proposal_actions = {
        proposal.action
        for proposal in proposals
    }

    required_count = (
        int(
            require_question_disposition
        )
        +
        int(
            require_answer_disposition
        )
    )

    required_proposal_count = 0

    if (
        require_question_disposition
        and question is not None
    ):
        required_proposal_count += 1

    if (
        require_answer_disposition
        and answer is not None
    ):
        required_proposal_count += 1

    all_required_present = (
        required_proposal_count
        == required_count
    )

    all_required_auto_fill = (
        all_required_present
        and all(
            proposal.action
            == "AUTO_FILL"
            for proposal
            in proposals
        )
    )

    if (
        all_required_auto_fill
        and not audit.review_required
        and not evidence.review_required
    ):
        reasons.append(
            (
                "All required dispositions have "
                "strong supporting evidence."
            )
        )

        return QuestionAutomationDecision(
            question_key=(
                audit.question_key
            ),
            action="AUTO_FILL",
            proposals=proposals,
            unresolved_sides=(
                unresolved_sides
            ),
            review_required=False,
            reasons=reasons,
        )

    if proposals:
        if unresolved_sides:
            reasons.append(
                (
                    "Some dispositions can be "
                    "prefilled, but other required "
                    "audit fields remain unresolved."
                )
            )

        elif (
            "PREFILL"
            in proposal_actions
        ):
            reasons.append(
                (
                    "All required dispositions "
                    "are available, but at least "
                    "one still requires human "
                    "confirmation."
                )
            )

        elif (
            audit.review_required
            or evidence.review_required
        ):
            reasons.append(
                (
                    "Disposition suggestions exist, "
                    "but the question window still "
                    "requires review."
                )
            )

        return QuestionAutomationDecision(
            question_key=(
                audit.question_key
            ),
            action="PREFILL",
            proposals=proposals,
            unresolved_sides=(
                unresolved_sides
            ),
            review_required=True,
            reasons=reasons,
        )

    reasons.append(
        (
            "No disposition is currently safe "
            "enough to prefill automatically."
        )
    )

    return QuestionAutomationDecision(
        question_key=audit.question_key,
        action="HUMAN_REVIEW",
        proposals=[],
        unresolved_sides=(
            unresolved_sides
        ),
        review_required=True,
        reasons=reasons,
    )