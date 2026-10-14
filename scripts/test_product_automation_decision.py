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


def disposition(
    disposition_id,
    text,
):
    return SuggestedDisposition(
        disposition_id=disposition_id,
        disposition_text=text,
        disposition_path=[text],
    )


def evidence(
    agent,
    respondent,
    followup="",
):
    return QuestionEvidence(
        agent_text=agent,
        respondent_text=respondent,
        agent_followup_text=followup,
    )


def show(
    name,
    decision,
):
    print()
    print("=" * 72)
    print(name)
    print("=" * 72)

    print(
        f"TAG ACTION: "
        f"{decision.action}"
    )

    print()

    if decision.proposals:
        print("DISPOSITIONS")

        for proposal in (
            decision.proposals
        ):
            print(
                f"  {proposal.side:8} "
                f"→ "
                f"{proposal.disposition.disposition_text}"
                f" "
                f"[{proposal.action}]"
            )

    else:
        print(
            "DISPOSITIONS: none"
        )

    print()

    print(
        "Unresolved:",
        decision.unresolved_sides,
    )

    print(
        "Review:",
        decision.review_required,
    )

    for reason in decision.reasons:
        print(
            f"Reason: {reason}"
        )


def main():
    bijnor_audit = (
        QuestionAuditResult(
            question_key="ac_name",
            evidence=evidence(
                (
                    "आपका विधानसभा क्षेत्र "
                    "बदलापुर है"
                ),
                "हाँ बिजनौर",
                "बिजनौर",
            ),
            question_validation_status=(
                "ASKED_RIGHT"
            ),
            question_validation_confidence=0.94,
            question_disposition=(
                disposition(
                    2001,
                    "Asked Right",
                )
            ),
            resolved_option="Bijnor",
            stored_option="Badlapur",
            answer_resolution_status=(
                "MISMATCH"
            ),
            answer_resolution_confidence=1.0,
            answer_disposition=(
                disposition(
                    6002,
                    "Mismatch",
                )
            ),
            review_required=False,
        )
    )

    bijnor_evidence = (
        CorroboratedEvidenceResult(
            resolved_option="Bijnor",
            stored_option="Badlapur",
            resolution_status="MISMATCH",
            evidence_strength="STRONG",
            automation_status=(
                "AUTO_FILL_CANDIDATE"
            ),
            direct_support_turn_ids=[
                "segment_017"
            ],
            review_required=False,
        )
    )

    prompted_audit = (
        QuestionAuditResult(
            question_key=(
                "state_govt_change"
            ),
            evidence=evidence(
                (
                    "क्या आप राज्य सरकार में "
                    "बदलाव देखना चाहते हैं "
                    "या नहीं"
                ),
                "हाँ",
                "हाँ बोल दीजिए",
            ),
            question_validation_status=(
                "ASKED_RIGHT"
            ),
            question_validation_confidence=1.0,
            question_disposition=(
                disposition(
                    2001,
                    "Asked Right",
                )
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
                disposition(
                    4001,
                    "Yes - Prompting Done",
                )
            ),
            review_required=False,
        )
    )

    prompted_evidence = (
        CorroboratedEvidenceResult(
            resolved_option="Yes",
            stored_option="Yes",
            resolution_status="MATCH",
            evidence_strength="STRONG",
            automation_status=(
                "AUTO_FILL_CANDIDATE"
            ),
            direct_support_turn_ids=[
                "segment_008"
            ],
            review_required=False,
        )
    )

    inflation_audit = (
        QuestionAuditResult(
            question_key=(
                "major_problems"
            ),
            evidence=evidence(
                (
                    "आपके हिसाब से इस समय "
                    "सबसे बड़ी समस्या क्या है"
                ),
                "महनाई",
            ),
            question_validation_status=(
                "ASKED_RIGHT"
            ),
            question_validation_confidence=1.0,
            question_disposition=(
                disposition(
                    2001,
                    "Asked Right",
                )
            ),
            resolved_option="Inflation",
            stored_option="Inflation",
            answer_resolution_status="MATCH",
            answer_resolution_confidence=0.73,
            answer_disposition=(
                disposition(
                    8001,
                    "Asked Right",
                )
            ),
            review_required=True,
        )
    )

    inflation_evidence = (
        CorroboratedEvidenceResult(
            resolved_option="Inflation",
            stored_option="Inflation",
            resolution_status="MATCH",
            evidence_strength="MODERATE",
            automation_status=(
                "PREFILL_CANDIDATE"
            ),
            direct_support_turn_ids=[
                "segment_019_part_03"
            ],
            unsafe_turn_ids=[
                "segment_020",
                "segment_021",
            ],
            review_required=True,
        )
    )

    corrupted_audit = (
        QuestionAuditResult(
            question_key=(
                "unknown_noisy_tag"
            ),
            evidence=evidence(
                "",
                "कितने बजे है आपके",
            ),
            question_validation_status=(
                "UNCERTAIN"
            ),
            review_required=True,
        )
    )

    corrupted_evidence = (
        CorroboratedEvidenceResult(
            stored_option="Inflation",
            evidence_strength="WEAK",
            automation_status=(
                "HUMAN_REVIEW"
            ),
            unsafe_turn_ids=[
                "segment_020",
                "segment_023",
            ],
            review_required=True,
        )
    )

    scenarios = [
        (
            "Bijnor mismatch",
            bijnor_audit,
            bijnor_evidence,
        ),
        (
            "Prompted Yes",
            prompted_audit,
            prompted_evidence,
        ),
        (
            "Inflation with noisy context",
            inflation_audit,
            inflation_evidence,
        ),
        (
            "Unreliable evidence",
            corrupted_audit,
            corrupted_evidence,
        ),
    ]

    for (
        name,
        audit,
        corroborated,
    ) in scenarios:
        decision = (
            decide_question_automation(
                audit,
                corroborated,
            )
        )

        show(
            name,
            decision,
        )


if __name__ == "__main__":
    main()