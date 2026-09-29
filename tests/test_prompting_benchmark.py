from src.full_sample.prompting_benchmark import (
    compare_prompting_prediction,
    evaluate_prompting_dialogue,
    extract_canonical_options,
    infer_human_prompting_label,
)


def make_turn(
    role,
    start,
    end,
    text,
    overlap=False,
):
    return {
        "role": role,
        "speaker_id": (
            "SPEAKER_00"
            if role == "agent"
            else "SPEAKER_01"
        ),
        "start_sec": start,
        "end_sec": end,
        "asr_status": "COMPLETE",
        "transcript": text,
        "cross_speaker_overlap": (
            overlap
        ),
    }


def test_human_no_prompting_precedence():
    payload = {
        "answer": (
            "Respondent answer "
            "without Prompting"
        ),
        "child": (
            "Yes - No Prompting Done"
        ),
    }

    assert (
        infer_human_prompting_label(
            payload
        )
        == "NO_PROMPTING"
    )


def test_human_prompting():
    payload = {
        "answer": (
            "Respondent answer "
            "after Prompting"
        ),
        "child": "Prompting - BSP",
    }

    assert (
        infer_human_prompting_label(
            payload
        )
        == "PROMPTING"
    )


def test_does_not_use_raw_response_as_options():
    entry = {
        "data": {
            "raw_response": "BSP",
        }
    }

    result = (
        extract_canonical_options(
            entry
        )
    )

    assert result == []


def test_extracts_explicit_options():
    entry = {
        "data": {
            "options": [
                {
                    "value": "BSP",
                    "hindiVal": "बसपा",
                },
                {
                    "value": "SP",
                    "hindiVal": "सपा",
                },
            ]
        }
    }

    result = (
        extract_canonical_options(
            entry
        )
    )

    assert len(result) == 2

    assert (
        result[0].value
        == "BSP"
    )

    assert (
        "बसपा"
        in result[0].labels
    )


def test_no_followup_is_no_prompting():
    dialogue = {
        "evidence_status": (
            "ROLE_DIALOGUE_AVAILABLE"
        ),
        "turns": [
            make_turn(
                "agent",
                10.0,
                12.0,
                "क्या आप बदलाव चाहते हैं",
            ),
            make_turn(
                "respondent",
                12.2,
                13.5,
                "हाँ बदलाव होना चाहिए",
            ),
        ],
    }

    question = {
        "start_sec": 10.0,
        "end_sec": 14.0,
    }

    result = (
        evaluate_prompting_dialogue(
            dialogue=dialogue,
            question_window=question,
            options=[],
        )
    )

    assert (
        result["prediction"]
        == "NO_PROMPTING"
    )


def test_missing_respondent_is_insufficient():
    dialogue = {
        "evidence_status": (
            "AGENT_ONLY_ASR"
        ),
        "turns": [
            make_turn(
                "agent",
                10.0,
                12.0,
                "question",
            ),
        ],
    }

    question = {
        "start_sec": 10.0,
        "end_sec": 14.0,
    }

    result = (
        evaluate_prompting_dialogue(
            dialogue=dialogue,
            question_window=question,
            options=[],
        )
    )

    assert (
        result["prediction"]
        == (
            "INSUFFICIENT_ROLE_EVIDENCE"
        )
    )


def test_existing_detector_can_detect_prompt():
    dialogue = {
        "evidence_status": (
            "ROLE_DIALOGUE_AVAILABLE"
        ),
        "turns": [
            make_turn(
                "agent",
                10.0,
                12.0,
                "किस पार्टी को चुनेंगे",
            ),
            make_turn(
                "respondent",
                12.2,
                13.0,
                "पता नहीं",
            ),
            make_turn(
                "agent",
                13.2,
                15.0,
                "बसपा बोल दीजिए",
            ),
        ],
    }

    policy = {
        "data": {
            "options": [
                {
                    "value": "BSP",
                    "hindiVal": "बसपा",
                }
            ]
        }
    }

    options = (
        extract_canonical_options(
            policy
        )
    )

    result = (
        evaluate_prompting_dialogue(
            dialogue=dialogue,
            question_window={
                "start_sec": 10.0,
                "end_sec": 16.0,
            },
            options=options,
        )
    )

    assert (
        result["prediction"]
        == "PROMPTING"
    )


def test_uncertain_not_scored_as_disagreement():
    result = (
        compare_prompting_prediction(
            prediction="UNCERTAIN",
            human_label="PROMPTING",
        )
    )

    assert result is None


def test_resolved_prediction_is_compared():
    result = (
        compare_prompting_prediction(
            prediction=(
                "NO_PROMPTING"
            ),
            human_label=(
                "NO_PROMPTING"
            ),
        )
    )

    assert result is True