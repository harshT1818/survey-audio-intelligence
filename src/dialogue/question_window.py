from src.dialogue.models import (
    QuestionDialogue,
    QuestionDialogueEvidence,
    SpeechTurn,
)


def _join_turn_texts(
    turns: list[SpeechTurn],
) -> str:
    return " ".join(
        turn.text.strip()
        for turn in turns
        if turn.text.strip()
    ).strip()


def extract_question_evidence(
    dialogue: QuestionDialogue,
) -> QuestionDialogueEvidence:

    turns = [
        turn
        for turn in dialogue.turns
        if turn.text.strip()
    ]

    if not turns:
        return QuestionDialogueEvidence(
            agent_question_text="",
            initial_respondent_text="",
            agent_followup_text="",
            final_respondent_text="",
            review_required=True,
            reason="No dialogue turns were provided.",
        )

    respondent_indexes = [
        index
        for index, turn in enumerate(turns)
        if turn.speaker == "respondent"
    ]

    if not respondent_indexes:
        return QuestionDialogueEvidence(
            agent_question_text=_join_turn_texts(
                [
                    turn
                    for turn in turns
                    if turn.speaker == "agent"
                ]
            ),
            initial_respondent_text="",
            agent_followup_text="",
            final_respondent_text="",
            start_sec=_get_start_sec(turns),
            end_sec=_get_end_sec(turns),
            review_required=True,
            reason=(
                "No respondent turn was found "
                "in the question dialogue."
            ),
        )

    first_respondent_index = respondent_indexes[0]
    last_respondent_index = respondent_indexes[-1]

    question_turns = [
        turn
        for turn in turns[
            :first_respondent_index
        ]
        if turn.speaker == "agent"
    ]

    initial_respondent_turn = turns[
        first_respondent_index
    ]

    followup_turns = [
        turn
        for turn in turns[
            first_respondent_index + 1:
            last_respondent_index
        ]
        if turn.speaker == "agent"
    ]

    final_respondent_turn = turns[
        last_respondent_index
    ]

    if (
        first_respondent_index
        == last_respondent_index
    ):
        final_respondent_text = (
            initial_respondent_turn.text.strip()
        )
    else:
        final_respondent_text = (
            final_respondent_turn.text.strip()
        )

    unknown_turns = [
        turn
        for turn in turns
        if turn.speaker == "unknown"
    ]

    review_required = bool(
        unknown_turns
    )

    reason = (
        "Dialogue evidence extracted successfully."
    )

    if unknown_turns:
        reason = (
            "Dialogue evidence was extracted, "
            "but one or more speaker turns have "
            "an unknown role."
        )

    return QuestionDialogueEvidence(
        agent_question_text=_join_turn_texts(
            question_turns
        ),
        initial_respondent_text=(
            initial_respondent_turn.text.strip()
        ),
        agent_followup_text=_join_turn_texts(
            followup_turns
        ),
        final_respondent_text=(
            final_respondent_text
        ),
        start_sec=_get_start_sec(turns),
        end_sec=_get_end_sec(turns),
        review_required=review_required,
        reason=reason,
    )


def _get_start_sec(
    turns: list[SpeechTurn],
) -> float | None:
    starts = [
        turn.start_sec
        for turn in turns
        if turn.start_sec is not None
    ]

    if not starts:
        return None

    return min(starts)


def _get_end_sec(
    turns: list[SpeechTurn],
) -> float | None:
    ends = [
        turn.end_sec
        for turn in turns
        if turn.end_sec is not None
    ]

    if not ends:
        return None

    return max(ends)