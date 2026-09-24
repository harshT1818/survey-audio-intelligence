from src.question_validation.fuzzy import (
    validate_question_text,
)


def test_exact_question_is_asked_right():
    result = validate_question_text(
        expected_question="आपकी उम्र क्या है?",
        transcript_text="सर आपकी उम्र क्या है?",
    )

    assert result.status == "ASKED_RIGHT"
    assert result.review_required is False
    assert result.confidence >= 0.82


def test_question_inside_longer_dialogue():
    result = validate_question_text(
        expected_question="आपकी उम्र क्या है?",
        transcript_text=(
            "ठीक है सर अब अगला सवाल आपकी उम्र क्या है "
            "छत्तीस साल"
        ),
    )

    assert result.status == "ASKED_RIGHT"
    assert result.review_required is False


def test_unrelated_transcript_is_uncertain():
    result = validate_question_text(
        expected_question="आपकी उम्र क्या है?",
        transcript_text="मैं बदलापुर में रहता हूं",
    )

    assert result.status == "UNCERTAIN"
    assert result.review_required is True


def test_empty_transcript_requires_review():
    result = validate_question_text(
        expected_question="आपकी उम्र क्या है?",
        transcript_text="",
    )

    assert result.status == "UNCERTAIN"
    assert result.review_required is True