from src.audit_engine.question_audit import (
    audit_question,
)
from src.audit_policy.parser import load_audit_project
from src.domain.models import SurveyQuestion
from src.resolver.models import CanonicalOption


def make_options():
    return [
        CanonicalOption(
            value="Badlapur",
            labels=["Badlapur", "बदलापुर"],
        ),
        CanonicalOption(
            value="Bijnor",
            labels=["Bijnor", "बिजनौर"],
        ),
    ]


def make_question():
    return SurveyQuestion(
        key="ac_name",
        text_hi="विधानसभा चुने",
        type="single_choice",
        options=[],
        selected_answer="Badlapur",
    )


def test_question_audit_match():
    policy = load_audit_project(
        "configs/sample_audit_project.json"
    )

    result = audit_question(
        question=make_question(),
        transcript_text="बदलापुर",
        canonical_options=make_options(),
        tag_policy=policy.tags["ac_name"],
        start_sec=10.0,
        end_sec=15.0,
    )

    assert result.question_key == "ac_name"

    assert result.evidence.transcript_text == "बदलापुर"
    assert result.evidence.start_sec == 10.0
    assert result.evidence.end_sec == 15.0

    assert result.resolved_option == "Badlapur"
    assert result.stored_option == "Badlapur"

    assert result.resolution_status == "MATCH"

    assert (
        result.suggested_disposition.disposition_text
        == "Asked Right"
    )

    assert result.review_required is False


def test_question_audit_mismatch():
    policy = load_audit_project(
        "configs/sample_audit_project.json"
    )

    result = audit_question(
        question=make_question(),
        transcript_text="बिजनौर",
        canonical_options=make_options(),
        tag_policy=policy.tags["ac_name"],
    )

    assert result.resolved_option == "Bijnor"
    assert result.stored_option == "Badlapur"

    assert result.resolution_status == "MISMATCH"

    assert (
        result.suggested_disposition.disposition_text
        == "Mismatch"
    )

    assert result.review_required is False