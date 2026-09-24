from src.domain.models import SurveyQuestion
from src.resolver.models import CanonicalOption
from src.resolver.question_resolver import (
    resolve_question_answer,
)


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


def test_question_answer_match():
    question = SurveyQuestion(
        key="ac_name",
        text_hi="विधानसभा चुने",
        type="single_choice",
        options=[],
        selected_answer="Badlapur",
    )

    result = resolve_question_answer(
        question=question,
        transcript_text="बदलापुर",
        canonical_options=make_options(),
    )

    assert result.resolved_option == "Badlapur"
    assert result.stored_option == "Badlapur"
    assert result.status == "MATCH"


def test_question_answer_mismatch():
    question = SurveyQuestion(
        key="ac_name",
        text_hi="विधानसभा चुने",
        type="single_choice",
        options=[],
        selected_answer="Badlapur",
    )

    result = resolve_question_answer(
        question=question,
        transcript_text="बिजनौर",
        canonical_options=make_options(),
    )

    assert result.resolved_option == "Bijnor"
    assert result.stored_option == "Badlapur"
    assert result.status == "MISMATCH"