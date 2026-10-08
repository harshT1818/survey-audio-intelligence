import pytest

from src.audit_policy.models import (
    AuditTagPolicy,
    DispositionNode,
    ValidationPolicy,
)
from src.domain.models import (
    SurveyQuestion,
)
from src.full_sample.audit_adapter import (
    build_safe_audit_inputs,
    run_full_question_audit,
)
from src.resolver.models import (
    CanonicalOption,
)


QUESTION_TEXT = (
    "क्या आप राज्य सरकार में "
    "बदलाव देखना चाहते हैं?"
)


def make_turn(
    turn_index,
    role,
    start_sec,
    end_sec,
    transcript,
    *,
    asr_status="COMPLETE",
    raw_overlap=False,
    raw_overlap_sec=0.0,
    cross_overlap=False,
):
    return {
        "turn_index": turn_index,
        "speaker_id": (
            "SPEAKER_00"
            if role == "agent"
            else "SPEAKER_01"
        ),
        "role": role,
        "start_sec": start_sec,
        "end_sec": end_sec,
        "asr_status": asr_status,
        "transcript": transcript,
        "raw_cross_speaker_overlap": (
            raw_overlap
        ),
        "raw_cross_speaker_overlap_sec": (
            raw_overlap_sec
        ),
        "cross_speaker_overlap": (
            cross_overlap
        ),
    }


def make_dialogue(
    turns,
):
    return {
        "tag": "state_govt_change",
        "question_text": (
            QUESTION_TEXT
        ),
        "evidence_status": (
            "ROLE_DIALOGUE_AVAILABLE"
        ),
        "turns": turns,
    }


def make_window():
    return {
        "tag": "state_govt_change",
        "question_text": (
            QUESTION_TEXT
        ),
        "start_sec": 9.0,
        "end_sec": 20.0,
    }


def make_question():
    return SurveyQuestion(
        key="state_govt_change",
        text_hi=QUESTION_TEXT,
        type="single_choice",
        options=[],
        selected_answer="Yes",
    )


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


def make_policy():
    return AuditTagPolicy(
        tag="state_govt_change",
        placeholder=(
            "State Government Change"
        ),
        project_code=(
            "FULL-SAMPLE-TEST"
        ),
        active=True,
        order=1,
        tag_type="console",
        question_tag_id=1,
        question_validation=(
            ValidationPolicy(
                enabled=True,
                validation_type=(
                    "single"
                ),
                dispositions=[
                    DispositionNode(
                        id=2001,
                        text=(
                            "Asked Right"
                        ),
                        children=[],
                    )
                ],
            )
        ),
        answer_validation=(
            ValidationPolicy(
                enabled=True,
                validation_type=(
                    "single"
                ),
                dispositions=[
                    DispositionNode(
                        id=3001,
                        text=(
                            "Asked Right"
                        ),
                        children=[],
                    ),
                    DispositionNode(
                        id=3002,
                        text="Mismatch",
                        children=[],
                    ),
                ],
            )
        ),
    )


@pytest.mark.parametrize("omit_start", [False, True])
def test_timestamp_less_agent_cannot_anchor_near_zero(omit_start):
    agent = make_turn(1, "agent", None, None, QUESTION_TEXT)
    if omit_start:
        agent.pop("start_sec")
    dialogue = make_dialogue([
        agent,
        make_turn(2, "respondent", 1.0, 2.0, "हाँ"),
    ])
    window = {**make_window(), "start_sec": 0.0}

    result = run_full_question_audit(
        question=make_question(),
        rich_dialogue=dialogue,
        question_window=window,
        canonical_options=make_options(),
        tag_policy=make_policy(),
    )

    assert result.trace.anchor_found is False
    assert result.trace.safe_audit_turn_count == 0
    assert result.trace.corroboration_turn_count == 0
    assert result.trace.review_required is True
    assert result.automation.action == "HUMAN_REVIEW"
    assert result.automation.review_required is True
    assert result.automation.proposals == []


def test_unrelated_question_withholds_audit_evidence():
    dialogue = make_dialogue([
        make_turn(1, "agent", 10.0, 12.0, "आज मौसम बहुत अच्छा है"),
        make_turn(2, "respondent", 12.5, 13.5, "हाँ"),
    ])

    result = run_full_question_audit(
        question=make_question(),
        rich_dialogue=dialogue,
        question_window=make_window(),
        canonical_options=make_options(),
        tag_policy=make_policy(),
    )

    assert result.trace.anchor_found is False
    assert result.trace.anchor_method == "QUESTION_TEXT_LOW_SIMILARITY"
    assert result.trace.safe_audit_turn_count == 0
    assert result.trace.corroboration_turn_count == 0
    assert result.trace.review_required is True
    assert result.automation.action == "HUMAN_REVIEW"
    assert result.automation.review_required is True
    assert result.automation.proposals == []


def test_unsafe_question_anchor_requires_review():
    dialogue = make_dialogue([
        make_turn(
            1, "agent", 10.0, 12.0, QUESTION_TEXT,
            raw_overlap=True, raw_overlap_sec=0.8,
        ),
        make_turn(2, "respondent", 12.5, 13.5, "हाँ"),
    ])

    inputs = build_safe_audit_inputs(
        dialogue=dialogue,
        question_window=make_window(),
    )
    assert inputs.trace.anchor_found is True
    assert inputs.dialogue.turns == []
    assert inputs.trace.safe_audit_turn_count == 0
    assert inputs.trace.review_required is True
    assert len(inputs.trace.rejected_turns) == 1
    assert inputs.trace.rejected_turns[0].material_for_review is True
    assert inputs.corroboration_turns[0].source_is_mixed is True
    assert inputs.corroboration_turns[0].upstream_review_required is True

    result = run_full_question_audit(
        question=make_question(),
        rich_dialogue=dialogue,
        question_window=make_window(),
        canonical_options=make_options(),
        tag_policy=make_policy(),
    )
    assert result.automation.action != "AUTO_FILL"
    assert result.automation.review_required is True
    assert all(p.action != "AUTO_FILL" for p in result.automation.proposals)


def test_adapter_removes_pre_anchor_turns():
    dialogue = make_dialogue(
        [
            make_turn(
                1,
                "respondent",
                5.0,
                6.0,
                "पुराना जवाब",
            ),
            make_turn(
                2,
                "agent",
                10.0,
                12.0,
                QUESTION_TEXT,
            ),
            make_turn(
                3,
                "respondent",
                12.5,
                13.5,
                "हाँ",
            ),
        ]
    )

    result = (
        build_safe_audit_inputs(
            dialogue=dialogue,
            question_window=(
                make_window()
            ),
        )
    )

    assert (
        result.trace.anchor_found
        is True
    )

    assert (
        result.trace.pre_anchor_turn_count
        == 1
    )

    assert [
        turn.text
        for turn
        in result.dialogue.turns
    ] == [
        QUESTION_TEXT,
        "हाँ",
    ]


def test_adapter_excludes_raw_overlap_from_audit_dialogue():
    dialogue = make_dialogue(
        [
            make_turn(
                1,
                "agent",
                10.0,
                12.0,
                QUESTION_TEXT,
            ),
            make_turn(
                2,
                "respondent",
                12.2,
                13.0,
                "आप बताइए",
                raw_overlap=True,
                raw_overlap_sec=0.8,
            ),
            make_turn(
                3,
                "respondent",
                13.2,
                14.0,
                "हाँ",
            ),
        ]
    )

    result = (
        build_safe_audit_inputs(
            dialogue=dialogue,
            question_window=(
                make_window()
            ),
        )
    )

    assert [
        turn.text
        for turn
        in result.dialogue.turns
    ] == [
        QUESTION_TEXT,
        "हाँ",
    ]

    assert len(
        result.trace.rejected_turns
    ) == 1

    rejected = (
        result.trace.rejected_turns[
            0
        ]
    )

    assert (
        rejected.material_for_review
        is True
    )

    assert (
        "RAW_CROSS_SPEAKER_OVERLAP"
        in rejected.reasons
    )


def test_raw_overlap_is_preserved_for_corroboration():
    dialogue = make_dialogue(
        [
            make_turn(
                1,
                "agent",
                10.0,
                12.0,
                QUESTION_TEXT,
            ),
            make_turn(
                2,
                "respondent",
                12.2,
                13.0,
                "आप बताइए",
                raw_overlap=True,
                raw_overlap_sec=0.8,
            ),
            make_turn(
                3,
                "respondent",
                13.2,
                14.0,
                "हाँ",
            ),
        ]
    )

    result = (
        build_safe_audit_inputs(
            dialogue=dialogue,
            question_window=(
                make_window()
            ),
        )
    )

    mixed = [
        turn
        for turn
        in result.corroboration_turns
        if turn.source_is_mixed
    ]

    assert len(
        mixed
    ) == 1

    assert (
        mixed[0]
        .upstream_review_required
        is True
    )


def test_tiny_skipped_turn_does_not_poison_corroboration():
    dialogue = make_dialogue(
        [
            make_turn(
                1,
                "agent",
                10.0,
                12.0,
                QUESTION_TEXT,
            ),
            make_turn(
                2,
                "respondent",
                12.05,
                12.07,
                "",
                asr_status=(
                    "SKIPPED_SHORT"
                ),
            ),
            make_turn(
                3,
                "respondent",
                12.5,
                13.5,
                "हाँ",
            ),
        ]
    )

    result = (
        build_safe_audit_inputs(
            dialogue=dialogue,
            question_window=(
                make_window()
            ),
        )
    )

    assert len(
        result.trace.rejected_turns
    ) == 1

    assert (
        result.trace.rejected_turns[
            0
        ].material_for_review
        is False
    )

    assert len(
        result.trace
        .ignored_short_turn_ids
    ) == 1

    assert all(
        turn.text
        for turn
        in result.corroboration_turns
    )


def test_missing_timestamps_are_preserved_as_none():
    dialogue = make_dialogue(
        [
            make_turn(
                1,
                "agent",
                10.0,
                12.0,
                QUESTION_TEXT,
            ),
            make_turn(
                2,
                "respondent",
                None,
                None,
                "हाँ",
            ),
        ]
    )

    result = build_safe_audit_inputs(
        dialogue=dialogue,
        question_window=make_window(),
    )

    assert result.trace.anchor_found is True

    assert len(result.dialogue.turns) == 2

    assert result.dialogue.turns[0].start_sec == 10.0
    assert result.dialogue.turns[0].end_sec == 12.0

    assert result.dialogue.turns[1].start_sec is None
    assert result.dialogue.turns[1].end_sec is None


def test_missing_timestamps_do_not_become_material_duration():
    dialogue = make_dialogue(
        [
            make_turn(
                1,
                "agent",
                10.0,
                12.0,
                QUESTION_TEXT,
            ),
            make_turn(
                2,
                "respondent",
                None,
                None,
                "कुछ",
                asr_status="ERROR",
            ),
            make_turn(
                3,
                "respondent",
                13.0,
                14.0,
                "हाँ",
            ),
        ]
    )

    result = (
        build_safe_audit_inputs(
            dialogue=dialogue,
            question_window=(
                make_window()
            ),
        )
    )

    rejected = [
        item
        for item
        in result.trace.rejected_turns
        if item.text == "कुछ"
    ]

    assert len(
        rejected
    ) == 1

    assert (
        rejected[0]
        .material_for_review
        is False
    )

    assert (
        rejected[0]
        .start_sec
        is None
    )

    assert (
        rejected[0]
        .end_sec
        is None
    )


def test_clean_question_can_auto_fill():
    dialogue = make_dialogue(
        [
            make_turn(
                1,
                "agent",
                10.0,
                12.0,
                QUESTION_TEXT,
            ),
            make_turn(
                2,
                "respondent",
                12.5,
                13.5,
                "हाँ",
            ),
        ]
    )

    result = (
        run_full_question_audit(
            question=make_question(),
            rich_dialogue=dialogue,
            question_window=(
                make_window()
            ),
            canonical_options=(
                make_options()
            ),
            tag_policy=(
                make_policy()
            ),
        )
    )

    assert (
        result.audit
        .question_validation_status
        == "ASKED_RIGHT"
    )

    assert (
        result.audit
        .answer_resolution_status
        == "MATCH"
    )

    assert (
        result.corroboration
        .resolved_option
        == "Yes"
    )

    assert (
        result.automation.action
        == "AUTO_FILL"
    )

    assert (
        result.automation
        .review_required
        is False
    )


def test_material_overlap_downgrades_auto_fill():
    dialogue = make_dialogue(
        [
            make_turn(
                1,
                "agent",
                10.0,
                12.0,
                QUESTION_TEXT,
            ),
            make_turn(
                2,
                "respondent",
                12.1,
                12.8,
                "कुछ",
                raw_overlap=True,
                raw_overlap_sec=0.7,
            ),
            make_turn(
                3,
                "respondent",
                13.0,
                14.0,
                "हाँ",
            ),
        ]
    )

    result = (
        run_full_question_audit(
            question=make_question(),
            rich_dialogue=dialogue,
            question_window=(
                make_window()
            ),
            canonical_options=(
                make_options()
            ),
            tag_policy=(
                make_policy()
            ),
        )
    )

    assert (
        result.audit
        .answer_resolution_status
        == "MATCH"
    )

    assert (
        result.trace.review_required
        is True
    )

    assert (
        result.corroboration
        .automation_status
        == "PREFILL_CANDIDATE"
    )

    assert (
        result.automation.action
        == "PREFILL"
    )

    assert (
        result.automation
        .review_required
        is True
    )
