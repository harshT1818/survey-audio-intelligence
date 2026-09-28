from src.evidence_quality.corroboration import (
    corroborate_answer_evidence,
)
from src.evidence_quality.corroboration_models import (
    CorroborationTurn,
)
from src.resolver.models import (
    CanonicalOption,
)


def _ac_options():
    return [
        CanonicalOption(
            value="Badlapur",
            labels=["बदलापुर"],
        ),
        CanonicalOption(
            value="Bijnor",
            labels=["बिजनौर"],
        ),
    ]


def _problem_options():
    return [
        CanonicalOption(
            value="Inflation",
            labels=["महंगाई"],
        ),
        CanonicalOption(
            value="Unemployment",
            labels=["बेरोजगारी"],
        ),
    ]


def test_clean_respondent_answer_can_auto_fill():
    result = corroborate_answer_evidence(
        turns=[
            CorroborationTurn(
                turn_id="r1",
                role="respondent",
                text="बिजनौर",
            ),
        ],
        options=_ac_options(),
        stored_option="Badlapur",
    )

    assert (
        result.resolved_option
        == "Bijnor"
    )

    assert (
        result.resolution_status
        == "MISMATCH"
    )

    assert (
        result.automation_status
        == "AUTO_FILL_CANDIDATE"
    )


def test_real_bijnor_exchange_recovers_from_bad_first_asr():
    result = corroborate_answer_evidence(
        turns=[
            CorroborationTurn(
                turn_id="15",
                role="respondent",
                text="नहीं बिजनेस",
            ),
            CorroborationTurn(
                turn_id="16",
                role="agent",
                text="बिजनौर",
            ),
            CorroborationTurn(
                turn_id="17",
                role="respondent",
                text="हाँ बिजनौर",
            ),
        ],
        options=_ac_options(),
        stored_option="Badlapur",
    )

    assert (
        result.resolved_option
        == "Bijnor"
    )

    assert (
        result.resolution_status
        == "MISMATCH"
    )

    assert (
        result.automation_status
        == "AUTO_FILL_CANDIDATE"
    )

    assert "17" in (
        result.direct_support_turn_ids
    )


def test_agent_entity_plus_yes_is_only_prefill():
    result = corroborate_answer_evidence(
        turns=[
            CorroborationTurn(
                turn_id="a1",
                role="agent",
                text="बिजनौर",
            ),
            CorroborationTurn(
                turn_id="r1",
                role="respondent",
                text="हाँ",
            ),
        ],
        options=_ac_options(),
        stored_option="Badlapur",
    )

    assert (
        result.resolved_option
        == "Bijnor"
    )

    assert (
        result.automation_status
        == "PREFILL_CANDIDATE"
    )

    assert result.review_required is True


def test_agent_directive_is_not_used_as_corroboration():
    result = corroborate_answer_evidence(
        turns=[
            CorroborationTurn(
                turn_id="a1",
                role="agent",
                text="बिजनौर बोल दीजिए",
            ),
            CorroborationTurn(
                turn_id="r1",
                role="respondent",
                text="हाँ",
            ),
        ],
        options=_ac_options(),
        stored_option="Badlapur",
    )

    assert (
        result.automation_status
        == "HUMAN_REVIEW"
    )


def test_moderate_asr_match_remains_prefill():
    result = corroborate_answer_evidence(
        turns=[
            CorroborationTurn(
                turn_id="r1",
                role="respondent",
                text="महनाई",
            ),
        ],
        options=_problem_options(),
        stored_option="Inflation",
    )

    assert (
        result.resolved_option
        == "Inflation"
    )

    assert (
        result.automation_status
        == "PREFILL_CANDIDATE"
    )


def test_agent_repetition_does_not_upgrade_moderate_to_auto_fill():
    result = corroborate_answer_evidence(
        turns=[
            CorroborationTurn(
                turn_id="r1",
                role="respondent",
                text="महनाई",
            ),
            CorroborationTurn(
                turn_id="a1",
                role="agent",
                text="महंगाई",
            ),
            CorroborationTurn(
                turn_id="r2",
                role="respondent",
                text="हाँ",
            ),
        ],
        options=_problem_options(),
        stored_option="Inflation",
    )

    assert (
        result.resolved_option
        == "Inflation"
    )

    assert (
        result.automation_status
        == "PREFILL_CANDIDATE"
    )


def test_conflicting_respondent_answers_require_review():
    result = corroborate_answer_evidence(
        turns=[
            CorroborationTurn(
                turn_id="r1",
                role="respondent",
                text="बदलापुर",
            ),
            CorroborationTurn(
                turn_id="r2",
                role="respondent",
                text="बिजनौर",
            ),
        ],
        options=_ac_options(),
        stored_option="Badlapur",
    )

    assert (
        result.automation_status
        == "HUMAN_REVIEW"
    )

    assert (
        len(
            result.conflicting_turn_ids
        )
        == 2
    )


def test_unknown_context_caps_strong_evidence_to_prefill():
    result = corroborate_answer_evidence(
        turns=[
            CorroborationTurn(
                turn_id="r1",
                role="respondent",
                text="महंगाई",
            ),
            CorroborationTurn(
                turn_id="u1",
                role="unknown",
                text="कितने बजे है आपके",
                upstream_review_required=True,
            ),
        ],
        options=_problem_options(),
        stored_option="Inflation",
    )

    assert (
        result.resolved_option
        == "Inflation"
    )

    assert (
        result.automation_status
        == "PREFILL_CANDIDATE"
    )

    assert "u1" in (
        result.unsafe_turn_ids
    )


def test_only_corrupted_unknown_evidence_requires_review():
    result = corroborate_answer_evidence(
        turns=[
            CorroborationTurn(
                turn_id="u1",
                role="unknown",
                text="कितने बजे है आपके",
                upstream_review_required=True,
            ),
        ],
        options=_problem_options(),
        stored_option="Inflation",
    )

    assert (
        result.automation_status
        == "HUMAN_REVIEW"
    )


def test_prompting_instruction_does_not_count_as_corroboration():
    options = [
        CanonicalOption(
            value="Yes",
            labels=["हाँ"],
        ),
        CanonicalOption(
            value="No",
            labels=["नहीं"],
        ),
    ]

    result = corroborate_answer_evidence(
        turns=[
            CorroborationTurn(
                turn_id="r1",
                role="respondent",
                text="मुझे पता नहीं",
            ),
            CorroborationTurn(
                turn_id="a1",
                role="agent",
                text="हाँ बोल दीजिए",
            ),
            CorroborationTurn(
                turn_id="r2",
                role="respondent",
                text="हाँ",
            ),
        ],
        options=options,
        stored_option="Yes",
    )

    assert (
        result.resolved_option
        == "Yes"
    )

    assert (
        result.automation_status
        == "AUTO_FILL_CANDIDATE"
    )

    assert (
        "a1"
        not in result.contextual_support_turn_ids
    )