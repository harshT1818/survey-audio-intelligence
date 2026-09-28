from src.audit_engine.models import (
    QuestionAuditResult,
    QuestionEvidence,
    SuggestedDisposition,
)
from src.automation.decision import (
    decide_question_automation,
)
from src.evidence_quality.corroboration_models import (
    CorroboratedEvidenceResult,
)


def _evidence():
    return QuestionEvidence(
        agent_text="question",
        respondent_text="answer",
    )


def _question_disposition():
    return SuggestedDisposition(
        disposition_id=2001,
        disposition_text="Asked Right",
        disposition_path=[
            "Asked Right"
        ],
    )


def _answer_disposition(
    text="Asked Right",
    disposition_id=3001,
):
    return SuggestedDisposition(
        disposition_id=disposition_id,
        disposition_text=text,
        disposition_path=[
            text
        ],
    )


def test_full_strong_evidence_auto_fills():
    audit = QuestionAuditResult(
        question_key="ac_name",
        evidence=_evidence(),
        question_validation_status=(
            "ASKED_RIGHT"
        ),
        question_validation_confidence=1.0,
        question_disposition=(
            _question_disposition()
        ),
        resolved_option="Bijnor",
        stored_option="Badlapur",
        answer_resolution_status=(
            "MISMATCH"
        ),
        answer_resolution_confidence=1.0,
        answer_disposition=(
            _answer_disposition(
                text="Mismatch",
                disposition_id=3002,
            )
        ),
        review_required=False,
    )

    corroborated = (
        CorroboratedEvidenceResult(
            resolved_option="Bijnor",
            stored_option="Badlapur",
            resolution_status="MISMATCH",
            evidence_strength="STRONG",
            automation_status=(
                "AUTO_FILL_CANDIDATE"
            ),
            review_required=False,
        )
    )

    result = decide_question_automation(
        audit,
        corroborated,
    )

    assert result.action == "AUTO_FILL"

    assert len(
        result.proposals
    ) == 2


def test_prompted_answer_can_auto_fill_correct_disposition():
    audit = QuestionAuditResult(
        question_key=(
            "state_govt_change"
        ),
        evidence=_evidence(),
        question_validation_status=(
            "ASKED_RIGHT"
        ),
        question_validation_confidence=1.0,
        question_disposition=(
            _question_disposition()
        ),
        resolved_option="Yes",
        stored_option="Yes",
        answer_resolution_status="MATCH",
        answer_resolution_confidence=1.0,
        prompting_status=(
            "PROMPTING_EVIDENCE"
        ),
        prompting_confidence=0.9,
        prompted_option="Yes",
        answer_disposition=(
            _answer_disposition(
                text=(
                    "Yes - Prompting Done"
                ),
                disposition_id=4001,
            )
        ),
        review_required=False,
    )

    corroborated = (
        CorroboratedEvidenceResult(
            resolved_option="Yes",
            stored_option="Yes",
            resolution_status="MATCH",
            evidence_strength="STRONG",
            automation_status=(
                "AUTO_FILL_CANDIDATE"
            ),
            review_required=False,
        )
    )

    result = decide_question_automation(
        audit,
        corroborated,
    )

    assert result.action == "AUTO_FILL"

    answer = [
        proposal
        for proposal
        in result.proposals
        if proposal.side
        == "answer"
    ][0]

    assert (
        answer.disposition
        .disposition_text
        == "Yes - Prompting Done"
    )


def test_moderate_answer_is_prefilled():
    audit = QuestionAuditResult(
        question_key=(
            "major_problems"
        ),
        evidence=_evidence(),
        question_validation_status=(
            "ASKED_RIGHT"
        ),
        question_validation_confidence=1.0,
        question_disposition=(
            _question_disposition()
        ),
        resolved_option="Inflation",
        stored_option="Inflation",
        answer_resolution_status="MATCH",
        answer_resolution_confidence=0.73,
        answer_disposition=(
            _answer_disposition()
        ),
        review_required=True,
    )

    corroborated = (
        CorroboratedEvidenceResult(
            resolved_option="Inflation",
            stored_option="Inflation",
            resolution_status="MATCH",
            evidence_strength="MODERATE",
            automation_status=(
                "PREFILL_CANDIDATE"
            ),
            unsafe_turn_ids=[
                "third_speaker"
            ],
            review_required=True,
        )
    )

    result = decide_question_automation(
        audit,
        corroborated,
    )

    assert result.action == "PREFILL"

    assert len(
        result.proposals
    ) == 2


def test_safe_question_can_still_be_prefilled_when_answer_unknown():
    audit = QuestionAuditResult(
        question_key=(
            "major_problems"
        ),
        evidence=_evidence(),
        question_validation_status=(
            "ASKED_RIGHT"
        ),
        question_validation_confidence=1.0,
        question_disposition=(
            _question_disposition()
        ),
        review_required=True,
    )

    corroborated = (
        CorroboratedEvidenceResult(
            stored_option="Inflation",
            evidence_strength="WEAK",
            automation_status=(
                "HUMAN_REVIEW"
            ),
            review_required=True,
        )
    )

    result = decide_question_automation(
        audit,
        corroborated,
    )

    assert result.action == "PREFILL"

    assert (
        "answer"
        in result.unresolved_sides
    )

    assert len(
        result.proposals
    ) == 1


def test_no_safe_dispositions_requires_human_review():
    audit = QuestionAuditResult(
        question_key="unknown_tag",
        evidence=_evidence(),
        question_validation_status=(
            "UNCERTAIN"
        ),
        review_required=True,
    )

    corroborated = (
        CorroboratedEvidenceResult(
            evidence_strength="WEAK",
            automation_status=(
                "HUMAN_REVIEW"
            ),
            review_required=True,
        )
    )

    result = decide_question_automation(
        audit,
        corroborated,
    )

    assert (
        result.action
        == "HUMAN_REVIEW"
    )

    assert (
        len(
            result.proposals
        )
        == 0
    )


def test_resolution_disagreement_blocks_answer_proposal():
    audit = QuestionAuditResult(
        question_key="ac_name",
        evidence=_evidence(),
        question_validation_status=(
            "ASKED_RIGHT"
        ),
        question_validation_confidence=1.0,
        question_disposition=(
            _question_disposition()
        ),
        resolved_option="Badlapur",
        stored_option="Badlapur",
        answer_resolution_status="MATCH",
        answer_disposition=(
            _answer_disposition()
        ),
        review_required=False,
    )

    corroborated = (
        CorroboratedEvidenceResult(
            resolved_option="Bijnor",
            stored_option="Badlapur",
            resolution_status="MISMATCH",
            evidence_strength="STRONG",
            automation_status=(
                "AUTO_FILL_CANDIDATE"
            ),
            review_required=False,
        )
    )

    result = decide_question_automation(
        audit,
        corroborated,
    )

    assert result.action == "PREFILL"

    assert (
        "answer"
        in result.unresolved_sides
    )