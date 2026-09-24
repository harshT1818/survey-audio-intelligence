from src.prompting.rules import detect_prompting
from src.resolver.models import CanonicalOption


def make_options():
    return [
        CanonicalOption(
            value="Yes",
            labels=[
                "Yes",
                "हाँ",
                "हां",
            ],
        ),
        CanonicalOption(
            value="No",
            labels=[
                "No",
                "नहीं",
                "नही",
            ],
        ),
    ]


def test_clear_prompting_after_uncertain_answer():
    result = detect_prompting(
        respondent_text="मुझे पता नहीं",
        agent_followup_text="हाँ बोल दीजिए",
        options=make_options(),
    )

    assert result.status == "PROMPTING_EVIDENCE"

    assert result.suggested_option == "Yes"

    assert result.review_required is False


def test_no_followup_means_no_prompting_evidence():
    result = detect_prompting(
        respondent_text="हाँ",
        agent_followup_text="",
        options=make_options(),
    )

    assert (
        result.status
        == "NO_PROMPTING_EVIDENCE"
    )

    assert result.suggested_option is None

    assert result.review_required is False


def test_reading_both_options_is_not_auto_prompting():
    result = detect_prompting(
        respondent_text="पता नहीं",
        agent_followup_text="हाँ या नहीं?",
        options=make_options(),
    )

    assert result.status == "UNCERTAIN"

    assert result.review_required is True


def test_single_option_without_directive_is_uncertain():
    result = detect_prompting(
        respondent_text="मालूम नहीं",
        agent_followup_text="हाँ?",
        options=make_options(),
    )

    assert result.status == "UNCERTAIN"

    assert result.review_required is True


def test_directive_without_uncertain_respondent_is_uncertain():
    result = detect_prompting(
        respondent_text="हाँ",
        agent_followup_text="हाँ बोल दीजिए",
        options=make_options(),
    )

    assert result.status == "UNCERTAIN"

    assert result.review_required is True