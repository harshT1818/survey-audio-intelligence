from src.evidence_quality.gate import (
    evaluate_answer_evidence,
)
from src.resolver.models import (
    CanonicalOption,
)


def test_exact_yes_is_auto_fill_candidate():
    result = evaluate_answer_evidence(
        raw_text="हाँ",
        options=[
            CanonicalOption(
                value="Yes",
                labels=["हाँ"],
            ),
            CanonicalOption(
                value="No",
                labels=["नहीं"],
            ),
        ],
        stored_option="Yes",
    )

    assert (
        result.evidence_status
        == "STRONG"
    )

    assert (
        result.automation_status
        == "AUTO_FILL_CANDIDATE"
    )


def test_uncertainty_requires_review():
    result = evaluate_answer_evidence(
        raw_text="मुझे पता नहीं",
        options=[
            CanonicalOption(
                value="Yes",
                labels=["हाँ"],
            ),
            CanonicalOption(
                value="No",
                labels=["नहीं"],
            ),
        ],
    )

    assert (
        result.automation_status
        == "HUMAN_REVIEW"
    )


def test_mixed_segment_requires_review():
    result = evaluate_answer_evidence(
        raw_text=(
            "छत्तीस साल ठीक है "
            "आपके हिसाब से समस्या क्या है"
        ),
        options=[
            CanonicalOption(
                value="36",
                labels=["छत्तीस साल"],
            ),
        ],
        source_is_mixed=True,
    )

    assert (
        result.automation_status
        == "HUMAN_REVIEW"
    )


def test_upstream_review_is_preserved():
    result = evaluate_answer_evidence(
        raw_text="महंगाई",
        options=[
            CanonicalOption(
                value="Inflation",
                labels=["महंगाई"],
            ),
        ],
        upstream_review_required=True,
    )

    assert (
        result.automation_status
        == "HUMAN_REVIEW"
    )


def test_question_like_text_requires_review():
    result = evaluate_answer_evidence(
        raw_text=(
            "आपके हिसाब से "
            "सबसे बड़ी समस्या क्या है"
        ),
        options=[
            CanonicalOption(
                value="Inflation",
                labels=["महंगाई"],
            ),
        ],
    )

    assert (
        result.automation_status
        == "HUMAN_REVIEW"
    )


def test_low_information_is_no_evidence():
    result = evaluate_answer_evidence(
        raw_text="ठीक है",
        options=[
            CanonicalOption(
                value="Yes",
                labels=["हाँ"],
            ),
        ],
    )

    assert (
        result.automation_status
        == "NO_EVIDENCE"
    )


def test_minor_asr_error_can_be_prefill_candidate():
    result = evaluate_answer_evidence(
        raw_text="महनाई",
        options=[
            CanonicalOption(
                value="Inflation",
                labels=[
                    "महंगाई",
                ],
            ),
            CanonicalOption(
                value="Unemployment",
                labels=[
                    "बेरोजगारी",
                ],
            ),
        ],
    )

    assert (
        result.automation_status
        == "PREFILL_CANDIDATE"
    )

    assert (
        result.resolved_option
        == "Inflation"
    )


def test_bad_bijnor_transcription_not_auto_filled():
    result = evaluate_answer_evidence(
        raw_text="नहीं बिजनेस",
        options=[
            CanonicalOption(
                value="Badlapur",
                labels=["बदलापुर"],
            ),
            CanonicalOption(
                value="Bijnor",
                labels=["बिजनौर"],
            ),
        ],
    )

    assert (
        result.automation_status
        == "HUMAN_REVIEW"
    )


def test_exact_bijnor_is_auto_fill_candidate():
    result = evaluate_answer_evidence(
        raw_text="बिजनौर",
        options=[
            CanonicalOption(
                value="Badlapur",
                labels=["बदलापुर"],
            ),
            CanonicalOption(
                value="Bijnor",
                labels=["बिजनौर"],
            ),
        ],
    )

    assert (
        result.automation_status
        == "AUTO_FILL_CANDIDATE"
    )


def test_nonsense_requires_review():
    result = evaluate_answer_evidence(
        raw_text="कितने बजे है आपके",
        options=[
            CanonicalOption(
                value="Inflation",
                labels=["महंगाई"],
            ),
            CanonicalOption(
                value="Unemployment",
                labels=["बेरोजगारी"],
            ),
        ],
    )

    assert (
        result.automation_status
        == "HUMAN_REVIEW"
    )