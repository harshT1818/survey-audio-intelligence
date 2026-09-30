from src.full_sample.evidence_diagnostics import (
    analyze_prompting_evaluation,
    detect_interviewer_like_text,
    find_option_mentions,
)
from src.resolver.models import (
    CanonicalOption,
)


def option(
    value,
    labels=None,
    aliases=None,
):
    return CanonicalOption(
        value=value,
        labels=labels or [],
        aliases=aliases or [],
    )


def test_detects_interviewer_like_respondent():
    markers = (
        detect_interviewer_like_text(
            (
                "तो किस कौन होना चाहिए "
                "आप बताइए"
            )
        )
    )

    assert markers


def test_normal_answer_not_interviewer_like():
    markers = (
        detect_interviewer_like_text(
            (
                "बदलाव जरूर "
                "होना चाहिए"
            )
        )
    )

    assert markers == []


def test_diagnostic_fuzzy_match_handles_mayawati_asr():
    options = [
        option(
            value=(
                "मायावती "
                "[Mayawati] *BSP*"
            ),
            labels=[
                "मायावती",
                "Mayawati",
            ],
            aliases=[
                "मायावती",
            ],
        )
    ]

    mentions = (
        find_option_mentions(
            text=(
                "या तो बहन मायवती हो "
                "एक नाम बताइए"
            ),
            options=options,
        )
    )

    assert len(
        mentions
    ) == 1

    assert (
        mentions[0][
            "option_value"
        ]
        == (
            "मायावती "
            "[Mayawati] *BSP*"
        )
    )


def test_pre_anchor_role_conflict_is_irrelevant():
    evaluation = {
        "prediction": (
            "NO_PROMPTING"
        ),
        "anchor_method": (
            "QUESTION_TEXT_SIMILARITY"
        ),
        "anchor_similarity": 0.88,
        "anchor_agent_turn": {
            "role": "agent",
            "start_sec": 13.0,
            "end_sec": 15.0,
            "transcript": (
                "क्या बदलाव चाहते हैं"
            ),
        },
        "initial_respondent_turn": {
            "role": "respondent",
            "speaker_id": "SPEAKER_01",
            "start_sec": 15.2,
            "end_sec": 16.2,
            "transcript": (
                "बदलाव होना चाहिए"
            ),
            "cross_speaker_overlap": (
                False
            ),
        },
        "agent_followup_turns": [],
    }

    result = (
        analyze_prompting_evaluation(
            evaluation=evaluation,
            options=[],
            stored_response=[],
            do_not_read_options=False,
        )
    )

    assert (
        "RESPONDENT_ROLE_CONFLICT"
        not in result[
            "safety_flags"
        ]
    )

    assert (
        result[
            "evidence_safety"
        ]
        == "SAFE_FOR_PROMPTING_RULES"
    )


def test_missing_post_anchor_respondent_is_review():
    evaluation = {
        "prediction": (
            "INSUFFICIENT_ROLE_EVIDENCE"
        ),
        "anchor_method": (
            "QUESTION_TEXT_SIMILARITY"
        ),
        "anchor_similarity": 0.90,
        "anchor_agent_turn": {
            "role": "agent",
            "start_sec": 10.0,
            "end_sec": 12.0,
            "transcript": "question",
        },
        "initial_respondent_turn": None,
        "agent_followup_turns": [],
    }

    result = (
        analyze_prompting_evaluation(
            evaluation=evaluation,
            options=[],
            stored_response=[],
            do_not_read_options=False,
        )
    )

    assert (
        "NO_USABLE_RESPONDENT_AFTER_ANCHOR"
        in result[
            "safety_flags"
        ]
    )

    assert (
        result[
            "evidence_safety"
        ]
        == "REVIEW"
    )


def test_respondent_role_conflict_is_local():
    evaluation = {
        "prediction": "UNCERTAIN",
        "anchor_method": (
            "QUESTION_TEXT_SIMILARITY"
        ),
        "anchor_similarity": 0.91,
        "anchor_agent_turn": {
            "role": "agent",
            "start_sec": 10.0,
            "end_sec": 12.0,
            "transcript": (
                "किसे विधायक देखना चाहते हैं"
            ),
        },
        "initial_respondent_turn": {
            "role": "respondent",
            "speaker_id": "SPEAKER_01",
            "start_sec": 13.0,
            "end_sec": 14.0,
            "transcript": (
                "तो किस कौन होना चाहिए "
                "आप बताइए"
            ),
            "cross_speaker_overlap": (
                False
            ),
        },
        "agent_followup_turns": [],
    }

    result = (
        analyze_prompting_evaluation(
            evaluation=evaluation,
            options=[],
            stored_response=[],
            do_not_read_options=True,
        )
    )

    assert (
        "RESPONDENT_ROLE_CONFLICT"
        in result[
            "safety_flags"
        ]
    )


def test_agent_only_selected_answer_is_review():
    options = [
        option(
            value=(
                "मायावती "
                "[Mayawati] *BSP*"
            ),
            labels=[
                "मायावती",
                "Mayawati",
            ],
            aliases=[
                "मायावती",
            ],
        )
    ]

    evaluation = {
        "prediction": "UNCERTAIN",
        "anchor_method": (
            "QUESTION_TEXT_SIMILARITY"
        ),
        "anchor_similarity": 0.88,
        "anchor_agent_turn": {
            "role": "agent",
            "start_sec": 10.0,
            "end_sec": 12.0,
            "transcript": (
                "मुख्यमंत्री किसे "
                "देखना चाहेंगे"
            ),
        },
        "initial_respondent_turn": {
            "role": "respondent",
            "speaker_id": "SPEAKER_01",
            "start_sec": 12.2,
            "end_sec": 12.6,
            "transcript": "हाँ हाँ",
            "cross_speaker_overlap": (
                False
            ),
        },
        "agent_followup_turns": [
            {
                "role": "agent",
                "speaker_id": (
                    "SPEAKER_00"
                ),
                "start_sec": 12.7,
                "end_sec": 17.0,
                "transcript": (
                    "एक नाम बताइए "
                    "मायवती होनी चाहिए"
                ),
                "cross_speaker_overlap": (
                    False
                ),
            }
        ],
    }

    result = (
        analyze_prompting_evaluation(
            evaluation=evaluation,
            options=options,
            stored_response=[
                (
                    "मायावती "
                    "[Mayawati] *BSP*"
                )
            ],
            do_not_read_options=True,
        )
    )

    assert (
        "SELECTED_ANSWER_AGENT_ONLY"
        in result[
            "safety_flags"
        ]
    )

    assert (
        "AGENT_DIRECTIVE_AND_STORED_ANSWER_SAME_TURN"
        in result[
            "observations"
        ]
    )