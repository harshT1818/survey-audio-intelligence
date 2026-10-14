from src.full_sample.safe_prompting import (
    evaluate_prompting_dialogue_safe,
)


def agent(
    start,
    end,
    text,
    *,
    raw_overlap=False,
):
    return {
        "role": "agent",
        "speaker_id": "SPEAKER_00",
        "start_sec": start,
        "end_sec": end,
        "asr_status": "COMPLETE",
        "transcript": text,
        "cross_speaker_overlap": False,
        "raw_cross_speaker_overlap": (
            raw_overlap
        ),
        "raw_cross_speaker_overlap_sec": (
            0.5
            if raw_overlap
            else 0.0
        ),
    }


def respondent(
    start,
    end,
    text,
    *,
    raw_overlap=False,
):
    return {
        "role": "respondent",
        "speaker_id": "SPEAKER_01",
        "start_sec": start,
        "end_sec": end,
        "asr_status": "COMPLETE",
        "transcript": text,
        "cross_speaker_overlap": False,
        "raw_cross_speaker_overlap": (
            raw_overlap
        ),
        "raw_cross_speaker_overlap_sec": (
            0.5
            if raw_overlap
            else 0.0
        ),
    }


def test_skips_contaminated_first_respondent():
    dialogue = {
        "evidence_status": (
            "ROLE_DIALOGUE_AVAILABLE"
        ),
        "question_text": (
            "आप विधायक के रूप में "
            "किसको देखना चाहते हैं?"
        ),
        "turns": [
            agent(
                10.0,
                12.0,
                (
                    "आप विधायक के रूप में "
                    "किसको देखना चाहते हैं"
                ),
            ),
            respondent(
                13.0,
                14.0,
                "आप बताइए",
                raw_overlap=True,
            ),
            respondent(
                15.0,
                16.0,
                (
                    "सही आदमी "
                    "होना चाहिए"
                ),
            ),
        ],
    }

    result = (
        evaluate_prompting_dialogue_safe(
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
            "initial_respondent_turn"
        ][
            "start_sec"
        ]
        == 15.0
    )

    assert len(
        result[
            "rejected_respondent_turns"
        ]
    ) == 1


def test_no_safe_respondent_is_insufficient():
    dialogue = {
        "evidence_status": (
            "ROLE_DIALOGUE_AVAILABLE"
        ),
        "question_text": (
            "आप किस पार्टी की सरकार "
            "देखना चाहते हैं?"
        ),
        "turns": [
            agent(
                10.0,
                12.0,
                (
                    "आप किस पार्टी की सरकार "
                    "देखना चाहते हैं"
                ),
            ),
            {
                "role": "respondent",
                "speaker_id": "SPEAKER_01",
                "start_sec": 12.2,
                "end_sec": 12.22,
                "asr_status": (
                    "SKIPPED_SHORT"
                ),
                "transcript": "",
                "cross_speaker_overlap": (
                    False
                ),
                "raw_cross_speaker_overlap": (
                    False
                ),
                "raw_cross_speaker_overlap_sec": (
                    0.0
                ),
            },
        ],
    }

    result = (
        evaluate_prompting_dialogue_safe(
            dialogue=dialogue,
            question_window={
                "start_sec": 9.0,
                "end_sec": 13.0,
            },
            options=[],
        )
    )

    assert (
        result["prediction"]
        == (
            "INSUFFICIENT_ROLE_EVIDENCE"
        )
    )

    assert (
        result[
            "initial_respondent_turn"
        ]
        is None
    )


def test_unsafe_agent_followup_is_removed():
    dialogue = {
        "evidence_status": (
            "ROLE_DIALOGUE_AVAILABLE"
        ),
        "question_text": (
            "क्या बदलाव चाहते हैं?"
        ),
        "turns": [
            agent(
                10.0,
                11.0,
                "क्या बदलाव चाहते हैं",
            ),
            respondent(
                11.2,
                12.0,
                "पता नहीं",
            ),
            agent(
                12.2,
                13.0,
                "हाँ बोल दीजिए",
                raw_overlap=True,
            ),
        ],
    }

    result = (
        evaluate_prompting_dialogue_safe(
            dialogue=dialogue,
            question_window={
                "start_sec": 9.0,
                "end_sec": 14.0,
            },
            options=[],
        )
    )

    assert (
        result[
            "agent_followup_turns"
        ]
        == []
    )

    assert len(
        result[
            "rejected_agent_followup_turns"
        ]
    ) == 1


def test_clean_direct_answer_can_resolve():
    dialogue = {
        "evidence_status": (
            "ROLE_DIALOGUE_AVAILABLE"
        ),
        "question_text": (
            "क्या बदलाव चाहते हैं?"
        ),
        "turns": [
            agent(
                10.0,
                11.0,
                "क्या बदलाव चाहते हैं",
            ),
            respondent(
                11.2,
                12.0,
                (
                    "हाँ बदलाव "
                    "होना चाहिए"
                ),
            ),
        ],
    }

    result = (
        evaluate_prompting_dialogue_safe(
            dialogue=dialogue,
            question_window={
                "start_sec": 9.0,
                "end_sec": 13.0,
            },
            options=[],
        )
    )

    assert (
        result[
            "prediction"
        ]
        == "NO_PROMPTING"
    )

    assert (
        result[
            "decision_safe"
        ]
        is True
    )