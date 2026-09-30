from src.full_sample.prompting_benchmark import (
    evaluate_prompting_dialogue,
    question_turn_similarity,
    select_question_anchor,
)


def agent_turn(
    start,
    end,
    text,
):
    return {
        "turn_index": 1,
        "speaker_id": "SPEAKER_00",
        "role": "agent",
        "start_sec": start,
        "end_sec": end,
        "asr_status": "COMPLETE",
        "transcript": text,
        "cross_speaker_overlap": False,
    }


def respondent_turn(
    start,
    end,
    text,
):
    return {
        "turn_index": 2,
        "speaker_id": "SPEAKER_01",
        "role": "respondent",
        "start_sec": start,
        "end_sec": end,
        "asr_status": "COMPLETE",
        "transcript": text,
        "cross_speaker_overlap": False,
    }


def test_question_similarity_prefers_real_question():
    question = (
        "उत्तर प्रदेश में 2027 के विधानसभा "
        "चुनाव के बाद में क्या आप राज्य सरकार "
        "में बदलाव देखना चाहते हैं या नहीं?"
    )

    irrelevant = (
        question_turn_similarity(
            question,
            "सरकार मायवती की बहुत अच्छी थी",
        )
    )

    actual = (
        question_turn_similarity(
            question,
            (
                "क्या आप राज्य सरकार बदलाव "
                "देखना चाहते हैं नहीं"
            ),
        )
    )

    assert actual > irrelevant
    assert actual >= 0.60


def test_anchor_is_not_first_agent_turn():
    dialogue = {
        "question_text": (
            "उत्तर प्रदेश में 2027 के विधानसभा "
            "चुनाव के बाद में क्या आप राज्य सरकार "
            "में बदलाव देखना चाहते हैं या नहीं?"
        ),
        "turns": [
            agent_turn(
                226.0,
                227.2,
                (
                    "सरकार मायवती की "
                    "बहुत अच्छी थी"
                ),
            ),
            respondent_turn(
                228.0,
                229.0,
                (
                    "आपको कौन अच्छी लगी"
                ),
            ),
            agent_turn(
                231.9,
                233.8,
                (
                    "क्या आप राज्य सरकार "
                    "बदलाव देखना चाहते हैं नहीं"
                ),
            ),
            respondent_turn(
                234.3,
                236.2,
                (
                    "नहीं अब बदलाव तो "
                    "होना चाहिए"
                ),
            ),
        ],
    }

    question_window = {
        "start_sec": 223.0,
        "end_sec": 238.0,
    }

    result = (
        select_question_anchor(
            dialogue=dialogue,
            question_window=(
                question_window
            ),
        )
    )

    assert (
        result["turn"][
            "start_sec"
        ]
        == 231.9
    )

    assert (
        result["method"]
        == "QUESTION_TEXT_SIMILARITY"
    )

    assert (
        result["score"]
        >= 0.60
    )


def test_evaluation_uses_respondent_after_matched_anchor():
    dialogue = {
        "evidence_status": (
            "ROLE_DIALOGUE_AVAILABLE"
        ),
        "question_text": (
            "क्या आप राज्य सरकार में "
            "बदलाव देखना चाहते हैं या नहीं?"
        ),
        "turns": [
            agent_turn(
                10.0,
                11.0,
                (
                    "पुरानी सरकार बहुत "
                    "अच्छी थी"
                ),
            ),
            respondent_turn(
                11.1,
                12.0,
                "आपको कौन अच्छी लगी",
            ),
            agent_turn(
                13.0,
                15.0,
                (
                    "क्या आप राज्य सरकार में "
                    "बदलाव देखना चाहते हैं "
                    "या नहीं"
                ),
            ),
            respondent_turn(
                15.2,
                16.5,
                (
                    "नहीं अब बदलाव तो "
                    "होना चाहिए"
                ),
            ),
        ],
    }

    result = (
        evaluate_prompting_dialogue(
            dialogue=dialogue,
            question_window={
                "start_sec": 9.0,
                "end_sec": 17.0,
            },
            options=[],
        )
    )

    assert (
        result[
            "anchor_agent_turn"
        ][
            "start_sec"
        ]
        == 13.0
    )

    assert (
        result[
            "initial_respondent_turn"
        ][
            "start_sec"
        ]
        == 15.2
    )


def test_low_similarity_anchor_is_withheld():
    dialogue = {
        "question_text": (
            "आप किस पार्टी की सरकार "
            "देखना चाहते हैं?"
        ),
        "turns": [
            agent_turn(
                10.0,
                11.0,
                "आज मौसम बहुत अच्छा है",
            ),
            respondent_turn(
                11.2,
                12.0,
                "हाँ",
            ),
        ],
    }

    result = (
        select_question_anchor(
            dialogue=dialogue,
            question_window={
                "start_sec": 9.0,
                "end_sec": 13.0,
            },
        )
    )

    assert result["turn"] is None

    assert (
        result["method"]
        == (
            "QUESTION_TEXT_LOW_SIMILARITY"
        )
    )