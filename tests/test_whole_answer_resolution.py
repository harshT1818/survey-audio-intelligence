from src.domain.models import SurveyQuestion
from src.evidence_quality.corroboration import (
    corroborate_answer_evidence,
)
from src.evidence_quality.corroboration_models import (
    CorroborationTurn,
)
from src.evidence_quality.gate import (
    evaluate_answer_evidence,
)
from src.resolver.closed_set import (
    resolve_closed_set_answer,
)
from src.resolver.models import (
    CanonicalOption,
)
from src.resolver.question_resolver import (
    resolve_question_answer,
)


# Synthetic Hindi yes/no answers. An option word inside a longer
# statement must not be read as that option: the statement can
# mean the opposite ("नहीं, बदलाव होना चाहिए" affirms change).

AFFIRMING_WITH_LEADING_NO = "नहीं अब बदलाव तो होना चाहिए"
REFUSING_WITH_JI = "नहीं जी मुझे कोई बदलाव नहीं चाहिए"


def yes_no_options():
    return [
        CanonicalOption(
            value="हाँ",
            labels=["हाँ"],
            aliases=["हां", "जी हाँ"],
        ),
        CanonicalOption(
            value="नहीं",
            labels=["नहीं"],
            aliases=["नही"],
        ),
    ]


def ac_options():
    return [
        CanonicalOption(
            value="Badlapur",
            labels=["बदलापुर"],
        ),
        CanonicalOption(
            value="Bijnor",
            labels=["बिजनौर"],
        ),
    ]


def test_option_inside_statement_is_uncertain_for_whole_answer():
    for text in (
        AFFIRMING_WITH_LEADING_NO,
        REFUSING_WITH_JI,
        "हाँ बिल्कुल बदलाव चाहिए",
    ):
        result = resolve_closed_set_answer(
            raw_text=text,
            options=yes_no_options(),
            stored_option="हाँ",
            require_whole_answer=True,
        )

        assert result.status == "UNCERTAIN", text
        assert result.resolved_option is None


def test_whole_answer_still_resolves_short_and_repeated_answers():
    for text, expected in (
        ("नहीं", "नहीं"),
        ("नहीं नहीं", "नहीं"),
        ("हाँ", "हाँ"),
        ("जी हाँ", "हाँ"),
    ):
        result = resolve_closed_set_answer(
            raw_text=text,
            options=yes_no_options(),
            require_whole_answer=True,
        )

        assert result.resolved_option == expected, text


def test_default_resolution_keeps_partial_matching_for_agent_text():
    result = resolve_closed_set_answer(
        raw_text="आपका विधानसभा क्षेत्र बिजनौर है",
        options=ac_options(),
    )

    assert result.resolved_option == "Bijnor"


def test_gate_does_not_mark_statement_as_strong_evidence():
    result = evaluate_answer_evidence(
        raw_text=AFFIRMING_WITH_LEADING_NO,
        options=yes_no_options(),
        stored_option="हाँ",
    )

    assert result.evidence_status == "WEAK"
    assert result.automation_status == "HUMAN_REVIEW"
    assert result.resolved_option is None
    assert result.review_required is True


def test_gate_does_not_prefill_opposite_option():
    result = evaluate_answer_evidence(
        raw_text=REFUSING_WITH_JI,
        options=yes_no_options(),
        stored_option="हाँ",
    )

    assert result.automation_status == "HUMAN_REVIEW"
    assert result.resolved_option is None


def test_corroboration_does_not_report_strong_mismatch_from_statement():
    result = corroborate_answer_evidence(
        turns=[
            CorroborationTurn(
                turn_id="a1",
                role="agent",
                text="क्या आप राज्य सरकार में बदलाव देखना चाहते हैं",
            ),
            CorroborationTurn(
                turn_id="r1",
                role="respondent",
                text=AFFIRMING_WITH_LEADING_NO,
            ),
        ],
        options=yes_no_options(),
        stored_option="हाँ",
    )

    assert result.automation_status == "HUMAN_REVIEW"
    assert result.resolution_status != "MISMATCH"
    assert result.direct_support_turn_ids == []
    assert result.review_required is True


def test_core_question_resolver_requires_whole_answer():
    question = SurveyQuestion(
        key="state_govt_change",
        type="single_choice",
        text_hi="क्या आप राज्य सरकार में बदलाव देखना चाहते हैं?",
        selected_answer="हाँ",
    )

    result = resolve_question_answer(
        question=question,
        transcript_text=AFFIRMING_WITH_LEADING_NO,
        canonical_options=yes_no_options(),
    )

    assert result.status == "UNCERTAIN"
    assert result.resolved_option is None
