from src.full_sample.prompting_dialogue import (
    build_prompting_dialogue,
    interval_overlap_sec,
)


def test_interval_overlap():
    result = interval_overlap_sec(
        10.0,
        12.0,
        11.5,
        13.0,
    )

    assert result == 0.5


def test_no_interval_overlap():
    result = interval_overlap_sec(
        10.0,
        11.0,
        12.0,
        13.0,
    )

    assert result == 0.0


def test_build_role_dialogue():
    manifest = [
        {
            "tag": "mla_choice",
            "question_index": 10,
            "question_text": "Question",
            "stored_response": "Rashid",
            "turn_index": 1,
            "speaker_id": "SPEAKER_00",
            "role": "agent",
            "role_confidence": "STRONG",
            "start_sec": 10.0,
            "end_sec": 12.0,
            "duration_sec": 2.0,
            "touches_core": True,
            "regions": ["core"],
            "export_for_asr": True,
            "audio_file": (
                "001_agent.wav"
            ),
        },
        {
            "tag": "mla_choice",
            "question_index": 10,
            "question_text": "Question",
            "stored_response": "Rashid",
            "turn_index": 2,
            "speaker_id": "SPEAKER_01",
            "role": "respondent",
            "role_confidence": "STRONG",
            "start_sec": 12.2,
            "end_sec": 13.5,
            "duration_sec": 1.3,
            "touches_core": True,
            "regions": ["core"],
            "export_for_asr": True,
            "audio_file": (
                "002_respondent.wav"
            ),
        },
    ]

    asr = [
        {
            "audio_file": (
                "001_agent.wav"
            ),
            "transcript": (
                "रशीद या याकूब"
            ),
        },
        {
            "audio_file": (
                "002_respondent.wav"
            ),
            "transcript": "रशीद",
        },
    ]

    result = (
        build_prompting_dialogue(
            manifest=manifest,
            asr_results=asr,
        )
    )

    assert len(result) == 1

    question = result[0]

    assert (
        question[
            "evidence_status"
        ]
        == "ROLE_DIALOGUE_AVAILABLE"
    )

    assert (
        question[
            "usable_agent_turn_count"
        ]
        == 1
    )

    assert (
        question[
            "usable_respondent_turn_count"
        ]
        == 1
    )

    assert (
        question["turns"][1][
            "transcript"
        ]
        == "रशीद"
    )


def test_short_turn_is_preserved():
    manifest = [
        {
            "tag": "test",
            "question_index": 1,
            "turn_index": 1,
            "speaker_id": "SPEAKER_01",
            "role": "respondent",
            "start_sec": 1.0,
            "end_sec": 1.2,
            "export_for_asr": False,
            "audio_file": None,
        }
    ]

    result = (
        build_prompting_dialogue(
            manifest=manifest,
            asr_results=[],
        )
    )

    turn = result[0][
        "turns"
    ][0]

    assert (
        turn["asr_status"]
        == "SKIPPED_SHORT"
    )

    assert (
        result[0][
            "skipped_short_count"
        ]
        == 1
    )


def test_cross_speaker_overlap_is_flagged():
    manifest = [
        {
            "tag": "test",
            "question_index": 1,
            "turn_index": 1,
            "speaker_id": "SPEAKER_00",
            "role": "agent",
            "start_sec": 10.0,
            "end_sec": 12.0,
            "export_for_asr": True,
            "audio_file": "agent.wav",
        },
        {
            "tag": "test",
            "question_index": 1,
            "turn_index": 2,
            "speaker_id": "SPEAKER_01",
            "role": "respondent",
            "start_sec": 11.5,
            "end_sec": 13.0,
            "export_for_asr": True,
            "audio_file": (
                "respondent.wav"
            ),
        },
    ]

    asr = [
        {
            "audio_file": "agent.wav",
            "transcript": "question",
        },
        {
            "audio_file": (
                "respondent.wav"
            ),
            "transcript": "answer",
        },
    ]

    result = (
        build_prompting_dialogue(
            manifest=manifest,
            asr_results=asr,
        )
    )

    second = result[0][
        "turns"
    ][1]

    assert (
        second[
            "cross_speaker_overlap"
        ]
        is True
    )

    assert (
        second[
            "overlap_with_previous_sec"
        ]
        == 0.5
    )