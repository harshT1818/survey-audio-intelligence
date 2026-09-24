from src.audit_engine.question_audit import (
    audit_question,
)
from src.audit_policy.models import (
    AuditTagPolicy,
    DispositionNode,
    ValidationPolicy,
)
from src.dialogue.models import (
    QuestionDialogue,
    SpeechTurn,
)
from src.domain.models import SurveyQuestion
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


def make_question():
    return SurveyQuestion(
        key="state_govt_change",
        text_hi=(
            "उत्तर प्रदेश में 2027 के विधानसभा चुनाव के बाद "
            "क्या आप राज्य सरकार में बदलाव देखना चाहते हैं या नहीं?"
        ),
        type="single_choice",
        options=[],
        selected_answer="Yes",
    )


def make_tag_policy():
    return AuditTagPolicy(
        tag="state_govt_change",
        placeholder="State Government Change",
        project_code="TEST-PROJECT",
        active=True,
        order=1,
        tag_type="console",
        question_tag_id=1,

        question_validation=ValidationPolicy(
            enabled=True,
            validation_type="single",
            dispositions=[
                DispositionNode(
                    id=2001,
                    text="Asked Right",
                    children=[],
                ),
            ],
        ),

        answer_validation=ValidationPolicy(
            enabled=True,
            validation_type="single",
            dispositions=[
                DispositionNode(
                    id=3000,
                    text=(
                        "Respondent answer "
                        "without Prompting"
                    ),
                    children=[
                        DispositionNode(
                            id=3001,
                            text=(
                                "Yes - "
                                "No Prompting Done"
                            ),
                            children=[],
                        ),
                    ],
                ),
                DispositionNode(
                    id=4000,
                    text=(
                        "Respondent answer "
                        "after Prompting"
                    ),
                    children=[
                        DispositionNode(
                            id=4001,
                            text=(
                                "Yes - "
                                "Prompting Done"
                            ),
                            children=[],
                        ),
                    ],
                ),
            ],
        ),
    )


def no_prompting_path():
    return [
        "Respondent answer without Prompting",
        "Yes - No Prompting Done",
    ]


def prompting_path():
    return [
        "Respondent answer after Prompting",
        "Yes - Prompting Done",
    ]


def test_full_question_audit_without_prompting():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text=(
                    "उत्तर प्रदेश में 2027 के विधानसभा चुनाव के बाद "
                    "क्या आप राज्य सरकार में बदलाव देखना चाहते हैं या नहीं"
                ),
            ),
            SpeechTurn(
                speaker="respondent",
                text="हाँ",
            ),
        ]
    )

    result = audit_question(
        question=make_question(),
        dialogue=dialogue,
        canonical_options=make_options(),
        tag_policy=make_tag_policy(),
        no_prompting_path=no_prompting_path(),
        prompting_path=prompting_path(),
    )

    assert (
        result.question_validation_status
        == "ASKED_RIGHT"
    )

    assert result.question_disposition is not None
    assert (
        result.question_disposition.disposition_id
        == 2001
    )

    assert (
        result.answer_resolution_status
        == "MATCH"
    )

    assert result.resolved_option == "Yes"
    assert result.stored_option == "Yes"

    assert (
        result.prompting_status
        == "NO_PROMPTING_EVIDENCE"
    )

    assert result.prompted_option is None

    assert result.answer_disposition is not None

    assert (
        result.answer_disposition.disposition_id
        == 3001
    )

    assert result.review_required is False


def test_full_prompting_sequence_maps_correctly():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text=(
                    "उत्तर प्रदेश में 2027 के विधानसभा चुनाव के बाद "
                    "क्या आप राज्य सरकार में बदलाव देखना चाहते हैं या नहीं"
                ),
            ),
            SpeechTurn(
                speaker="respondent",
                text="मुझे पता नहीं",
            ),
            SpeechTurn(
                speaker="agent",
                text="हाँ बोल दीजिए",
            ),
            SpeechTurn(
                speaker="respondent",
                text="हाँ",
            ),
        ]
    )

    result = audit_question(
        question=make_question(),
        dialogue=dialogue,
        canonical_options=make_options(),
        tag_policy=make_tag_policy(),
        no_prompting_path=no_prompting_path(),
        prompting_path=prompting_path(),
    )

    assert (
        result.question_validation_status
        == "ASKED_RIGHT"
    )

    assert (
        result.prompting_status
        == "PROMPTING_EVIDENCE"
    )

    assert result.prompted_option == "Yes"

    assert (
        result.answer_resolution_status
        == "MATCH"
    )

    assert result.resolved_option == "Yes"

    assert result.answer_disposition is not None

    assert (
        result.answer_disposition.disposition_id
        == 4001
    )

    assert (
        result.answer_disposition.disposition_text
        == "Yes - Prompting Done"
    )

    assert result.review_required is False


def test_ambiguous_prompting_requires_review():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text=(
                    "उत्तर प्रदेश में 2027 के विधानसभा चुनाव के बाद "
                    "क्या आप राज्य सरकार में बदलाव देखना चाहते हैं या नहीं"
                ),
            ),
            SpeechTurn(
                speaker="respondent",
                text="पता नहीं",
            ),
            SpeechTurn(
                speaker="agent",
                text="हाँ या नहीं?",
            ),
            SpeechTurn(
                speaker="respondent",
                text="हाँ",
            ),
        ]
    )

    result = audit_question(
        question=make_question(),
        dialogue=dialogue,
        canonical_options=make_options(),
        tag_policy=make_tag_policy(),
        no_prompting_path=no_prompting_path(),
        prompting_path=prompting_path(),
    )

    assert (
        result.prompting_status
        == "UNCERTAIN"
    )

    assert result.answer_disposition is not None

    assert (
        result.answer_disposition.disposition_id
        is None
    )

    assert result.review_required is True


def test_unknown_speaker_turn_requires_review():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text=(
                    "उत्तर प्रदेश में 2027 के विधानसभा चुनाव के बाद "
                    "क्या आप राज्य सरकार में बदलाव देखना चाहते हैं या नहीं"
                ),
            ),
            SpeechTurn(
                speaker="unknown",
                text="कुछ आवाज",
            ),
            SpeechTurn(
                speaker="respondent",
                text="हाँ",
            ),
        ]
    )

    result = audit_question(
        question=make_question(),
        dialogue=dialogue,
        canonical_options=make_options(),
        tag_policy=make_tag_policy(),
        no_prompting_path=no_prompting_path(),
        prompting_path=prompting_path(),
    )

    assert result.review_required is True

    assert any(
        "unknown role" in reason
        for reason in result.reasons
    )


def test_dialogue_timing_is_preserved():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text=(
                    "उत्तर प्रदेश में 2027 के विधानसभा चुनाव के बाद "
                    "क्या आप राज्य सरकार में बदलाव देखना चाहते हैं या नहीं"
                ),
                start_sec=10.0,
                end_sec=15.0,
            ),
            SpeechTurn(
                speaker="respondent",
                text="हाँ",
                start_sec=15.5,
                end_sec=16.2,
            ),
        ]
    )

    result = audit_question(
        question=make_question(),
        dialogue=dialogue,
        canonical_options=make_options(),
        tag_policy=make_tag_policy(),
        no_prompting_path=no_prompting_path(),
        prompting_path=prompting_path(),
    )

    assert result.evidence.start_sec == 10.0
    assert result.evidence.end_sec == 16.2