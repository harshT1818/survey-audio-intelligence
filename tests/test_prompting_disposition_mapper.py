from src.audit_policy.models import (
    AuditTagPolicy,
    DispositionNode,
    ValidationPolicy,
)
from src.audit_policy.prompting_mapper import (
    map_prompting_answer_disposition,
)
from src.prompting.models import PromptingEvidence
from src.resolver.models import AnswerResolution


def make_tag_policy():
    return AuditTagPolicy(
        tag="state_govt_change",
        placeholder="State Government Change",
        project_code="TEST-PROJECT",
        active=True,
        order=1,
        tag_type="console",
        question_tag_id=1,

        question_validation=ValidationPolicy(
            enabled=True,
            validation_type="single",
            dispositions=[],
        ),

        answer_validation=ValidationPolicy(
            enabled=True,
            validation_type="single",
            dispositions=[
                DispositionNode(
                    id=3000,
                    text="Respondent answer without Prompting",
                    children=[
                        DispositionNode(
                            id=3001,
                            text="Yes - No Prompting Done",
                            children=[],
                        ),
                    ],
                ),
                DispositionNode(
                    id=4000,
                    text="Respondent answer after Prompting",
                    children=[
                        DispositionNode(
                            id=4001,
                            text="Yes - Prompting Done",
                            children=[],
                        ),
                    ],
                ),
            ],
        ),
    )


def make_matching_resolution():
    return AnswerResolution(
        raw_text="हाँ",
        resolved_option="Yes",
        stored_option="Yes",
        status="MATCH",
        confidence=1.0,
        candidates=[],
    )


def test_match_without_prompting_maps_to_no_prompting_leaf():
    prompting = PromptingEvidence(
        status="NO_PROMPTING_EVIDENCE",
        confidence=0.95,
        agent_followup_text="",
        respondent_text="हाँ",
        suggested_option=None,
        review_required=False,
        reason="No prompting evidence.",
    )

    result = map_prompting_answer_disposition(
        resolution=make_matching_resolution(),
        prompting=prompting,
        tag_policy=make_tag_policy(),
        no_prompting_path=[
            "Respondent answer without Prompting",
            "Yes - No Prompting Done",
        ],
        prompting_path=[
            "Respondent answer after Prompting",
            "Yes - Prompting Done",
        ],
    )

    assert result.status == "SUGGESTED"
    assert result.disposition_id == 3001
    assert (
        result.disposition_text
        == "Yes - No Prompting Done"
    )
    assert result.review_required is False


def test_match_with_prompting_maps_to_prompting_leaf():
    prompting = PromptingEvidence(
        status="PROMPTING_EVIDENCE",
        confidence=0.9,
        agent_followup_text="हाँ बोल दीजिए",
        respondent_text="मुझे पता नहीं",
        suggested_option="Yes",
        review_required=False,
        reason="Clear prompting evidence.",
    )

    result = map_prompting_answer_disposition(
        resolution=make_matching_resolution(),
        prompting=prompting,
        tag_policy=make_tag_policy(),
        no_prompting_path=[
            "Respondent answer without Prompting",
            "Yes - No Prompting Done",
        ],
        prompting_path=[
            "Respondent answer after Prompting",
            "Yes - Prompting Done",
        ],
    )

    assert result.status == "SUGGESTED"
    assert result.disposition_id == 4001
    assert (
        result.disposition_text
        == "Yes - Prompting Done"
    )
    assert result.review_required is False


def test_uncertain_prompting_requires_review():
    prompting = PromptingEvidence(
        status="UNCERTAIN",
        confidence=0.5,
        agent_followup_text="हाँ?",
        respondent_text="पता नहीं",
        suggested_option="Yes",
        review_required=True,
        reason="Prompting evidence is ambiguous.",
    )

    result = map_prompting_answer_disposition(
        resolution=make_matching_resolution(),
        prompting=prompting,
        tag_policy=make_tag_policy(),
        no_prompting_path=[
            "Respondent answer without Prompting",
            "Yes - No Prompting Done",
        ],
        prompting_path=[
            "Respondent answer after Prompting",
            "Yes - Prompting Done",
        ],
    )

    assert result.status == "UNCERTAIN"
    assert result.disposition_id is None
    assert result.review_required is True


def test_answer_mismatch_does_not_use_prompting_mapping():
    resolution = AnswerResolution(
        raw_text="नहीं",
        resolved_option="No",
        stored_option="Yes",
        status="MISMATCH",
        confidence=1.0,
        candidates=[],
    )

    prompting = PromptingEvidence(
        status="NO_PROMPTING_EVIDENCE",
        confidence=0.95,
        agent_followup_text="",
        respondent_text="नहीं",
        suggested_option=None,
        review_required=False,
        reason="No prompting evidence.",
    )

    result = map_prompting_answer_disposition(
        resolution=resolution,
        prompting=prompting,
        tag_policy=make_tag_policy(),
        no_prompting_path=[
            "Respondent answer without Prompting",
            "Yes - No Prompting Done",
        ],
        prompting_path=[
            "Respondent answer after Prompting",
            "Yes - Prompting Done",
        ],
    )

    assert result.status == "UNCERTAIN"
    assert result.disposition_id is None
    assert result.review_required is True


def test_missing_configured_path_requires_review():
    prompting = PromptingEvidence(
        status="NO_PROMPTING_EVIDENCE",
        confidence=0.95,
        agent_followup_text="",
        respondent_text="हाँ",
        suggested_option=None,
        review_required=False,
        reason="No prompting evidence.",
    )

    result = map_prompting_answer_disposition(
        resolution=make_matching_resolution(),
        prompting=prompting,
        tag_policy=make_tag_policy(),
        no_prompting_path=[
            "Something that does not exist",
        ],
        prompting_path=[
            "Respondent answer after Prompting",
            "Yes - Prompting Done",
        ],
    )

    assert result.status == "NO_MAPPING"
    assert result.disposition_id is None
    assert result.review_required is True