from src.speaker_roles.models import (
    RawSpeakerTurn,
)
from src.speaker_roles.rules import (
    infer_speaker_roles,
)


def test_survey_question_is_agent():
    result = infer_speaker_roles(
        [
            RawSpeakerTurn(
                segment_id="1",
                speaker_id="SPEAKER_01",
                text=(
                    "क्या आप राज्य सरकार में "
                    "बदलाव देखना चाहते हैं या नहीं"
                ),
            ),
        ]
    )

    assert result.turns[0].role == "agent"


def test_uncertainty_is_respondent():
    result = infer_speaker_roles(
        [
            RawSpeakerTurn(
                segment_id="1",
                speaker_id="SPEAKER_00",
                text="मुझे पता नहीं",
            ),
        ]
    )

    assert (
        result.turns[0].role
        == "respondent"
    )


def test_prompting_instruction_is_agent():
    result = infer_speaker_roles(
        [
            RawSpeakerTurn(
                segment_id="1",
                speaker_id="SPEAKER_01",
                text="हाँ बोल दीजिए",
            ),
        ]
    )

    assert result.turns[0].role == "agent"


def test_okay_is_agent_procedural():
    result = infer_speaker_roles(
        [
            RawSpeakerTurn(
                segment_id="1",
                speaker_id="SPEAKER_01",
                text="ठीक है",
            ),
        ]
    )

    assert result.turns[0].role == "agent"


def test_yes_no_followup_is_agent():
    result = infer_speaker_roles(
        [
            RawSpeakerTurn(
                segment_id="1",
                speaker_id="SPEAKER_01",
                text="हाँ या नहीं",
            ),
        ]
    )

    assert result.turns[0].role == "agent"


def test_short_answer_after_question_overrides_bad_speaker_id():
    result = infer_speaker_roles(
        [
            RawSpeakerTurn(
                segment_id="11",
                speaker_id="SPEAKER_01",
                text="हाँ या नहीं",
            ),
            RawSpeakerTurn(
                segment_id="12",
                speaker_id="SPEAKER_01",
                text="नहीं",
            ),
        ]
    )

    assert result.turns[0].role == "agent"

    assert (
        result.turns[1].role
        == "respondent"
    )


def test_question_overrides_bad_diarization_cluster():
    result = infer_speaker_roles(
        [
            RawSpeakerTurn(
                segment_id="17",
                speaker_id="SPEAKER_00",
                text="हाँ बिजनौर",
            ),
            RawSpeakerTurn(
                segment_id="18",
                speaker_id="SPEAKER_00",
                text="ठीक है आपकी उम्र क्या है",
            ),
        ]
    )

    assert (
        result.turns[0].role
        == "respondent"
    )

    assert result.turns[1].role == "agent"


def test_mixed_question_answer_segment_requires_review():
    result = infer_speaker_roles(
        [
            RawSpeakerTurn(
                segment_id="19",
                speaker_id="SPEAKER_00",
                text=(
                    "छत्तीस साल ठीक है "
                    "आपके हिसाब से इस समय "
                    "सबसे बड़ी समस्या क्या है"
                ),
            ),
        ]
    )

    turn = result.turns[0]

    assert turn.role == "unknown"
    assert turn.review_required is True


def test_question_and_uncertainty_same_segment_requires_review():
    result = infer_speaker_roles(
        [
            RawSpeakerTurn(
                segment_id="28",
                speaker_id="SPEAKER_00",
                text=(
                    "ठीक है आप मुख्यमंत्री के रूप में "
                    "किसे देखना चाहेंगे "
                    "अभी डिसाइड नहीं किया"
                ),
            ),
        ]
    )

    turn = result.turns[0]

    assert turn.role == "unknown"
    assert turn.review_required is True


def test_dominant_speaker_ids():
    result = infer_speaker_roles(
        [
            RawSpeakerTurn(
                segment_id="1",
                speaker_id="SPEAKER_01",
                text="क्या आप उत्तर प्रदेश के निवासी हैं",
            ),
            RawSpeakerTurn(
                segment_id="2",
                speaker_id="SPEAKER_00",
                text="हाँ",
            ),
            RawSpeakerTurn(
                segment_id="3",
                speaker_id="SPEAKER_01",
                text="आपकी उम्र क्या है",
            ),
            RawSpeakerTurn(
                segment_id="4",
                speaker_id="SPEAKER_00",
                text="छत्तीस साल",
            ),
        ]
    )

    assert (
        result.dominant_agent_speaker_id
        == "SPEAKER_01"
    )

    assert (
        result.dominant_respondent_speaker_id
        == "SPEAKER_00"
    )