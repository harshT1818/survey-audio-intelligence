from src.audit_policy.parser import load_audit_project
from src.audit_policy.question_mapper import (
    map_question_validation_to_disposition,
)
from src.question_validation.fuzzy import (
    validate_question_text,
)


def test_asked_right_maps_to_question_disposition():
    policy = load_audit_project(
        "configs/sample_audit_project.json"
    )

    tag_policy = policy.tags["state_govt_change"]

    validation = validate_question_text(
        expected_question=(
            "उत्तर प्रदेश में 2027 के विधानसभा चुनाव के बाद "
            "क्या आप राज्य सरकार में बदलाव देखना चाहते हैं या नहीं?"
        ),
        transcript_text=(
            "उत्तर प्रदेश में 2027 के विधानसभा चुनाव के बाद "
            "क्या आप राज्य सरकार में बदलाव देखना चाहते हैं या नहीं"
        ),
    )

    suggestion = map_question_validation_to_disposition(
        validation=validation,
        tag_policy=tag_policy,
    )

    assert suggestion.status == "SUGGESTED"
    assert suggestion.disposition_text == "Asked Right"
    assert suggestion.disposition_id is not None
    assert suggestion.review_required is False


def test_uncertain_question_requires_review():
    policy = load_audit_project(
        "configs/sample_audit_project.json"
    )

    tag_policy = policy.tags["state_govt_change"]

    validation = validate_question_text(
        expected_question=(
            "उत्तर प्रदेश में 2027 के विधानसभा चुनाव के बाद "
            "क्या आप राज्य सरकार में बदलाव देखना चाहते हैं या नहीं?"
        ),
        transcript_text="आप किस पार्टी को पसंद करते हैं?",
    )

    suggestion = map_question_validation_to_disposition(
        validation=validation,
        tag_policy=tag_policy,
    )

    assert suggestion.status == "UNCERTAIN"
    assert suggestion.disposition_id is None
    assert suggestion.review_required is True