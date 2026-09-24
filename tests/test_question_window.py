from src.dialogue.models import (
    QuestionDialogue,
    SpeechTurn,
)
from src.dialogue.question_window import (
    extract_question_evidence,
)


def test_simple_question_answer():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text="क्या आप बदलाव चाहते हैं?",
            ),
            SpeechTurn(
                speaker="respondent",
                text="हाँ",
            ),
        ]
    )

    evidence = extract_question_evidence(
        dialogue
    )

    assert (
        evidence.agent_question_text
        == "क्या आप बदलाव चाहते हैं?"
    )

    assert (
        evidence.initial_respondent_text
        == "हाँ"
    )

    assert (
        evidence.final_respondent_text
        == "हाँ"
    )

    assert (
        evidence.agent_followup_text
        == ""
    )

    assert evidence.review_required is False


def test_prompting_sequence_is_preserved():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text="क्या आप बदलाव चाहते हैं?",
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

    evidence = extract_question_evidence(
        dialogue
    )

    assert (
        evidence.agent_question_text
        == "क्या आप बदलाव चाहते हैं?"
    )

    assert (
        evidence.initial_respondent_text
        == "मुझे पता नहीं"
    )

    assert (
        evidence.agent_followup_text
        == "हाँ बोल दीजिए"
    )

    assert (
        evidence.final_respondent_text
        == "हाँ"
    )

    assert evidence.review_required is False


def test_multiple_agent_followups_are_joined():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text="क्या आप बदलाव चाहते हैं?",
            ),
            SpeechTurn(
                speaker="respondent",
                text="पता नहीं",
            ),
            SpeechTurn(
                speaker="agent",
                text="सोच लीजिए",
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

    evidence = extract_question_evidence(
        dialogue
    )

    assert (
        evidence.initial_respondent_text
        == "पता नहीं"
    )

    assert (
        evidence.agent_followup_text
        == "सोच लीजिए हाँ या नहीं?"
    )

    assert (
        evidence.final_respondent_text
        == "हाँ"
    )


def test_unknown_speaker_requires_review():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text="क्या आप बदलाव चाहते हैं?",
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

    evidence = extract_question_evidence(
        dialogue
    )

    assert evidence.review_required is True

    assert (
        "unknown role"
        in evidence.reason
    )


def test_timing_window_is_preserved():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text="क्या आप बदलाव चाहते हैं?",
                start_sec=10.0,
                end_sec=13.0,
            ),
            SpeechTurn(
                speaker="respondent",
                text="हाँ",
                start_sec=13.5,
                end_sec=14.2,
            ),
        ]
    )

    evidence = extract_question_evidence(
        dialogue
    )

    assert evidence.start_sec == 10.0
    assert evidence.end_sec == 14.2


def test_missing_respondent_requires_review():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text="क्या आप बदलाव चाहते हैं?",
            ),
        ]
    )

    evidence = extract_question_evidence(
        dialogue
    )

    assert evidence.review_required is True

    assert evidence.initial_respondent_text == ""
    assert evidence.final_respondent_text == ""


def test_empty_dialogue_requires_review():
    dialogue = QuestionDialogue(
        turns=[]
    )

    evidence = extract_question_evidence(
        dialogue
    )

    assert evidence.review_required is True