from src.audit_engine.models import (
    QuestionAuditResult,
    QuestionEvidence,
    SuggestedDisposition,
)
from src.audit_policy.answer_tree import (
    FLAT_PROMPTING,
    INTRODUCTION,
    MATCH_MISMATCH,
    NESTED_PROMPTING,
    UNSUPPORTED,
    answer_prompting_paths,
    classify_answer_tree,
)
from src.audit_policy.mapper import (
    map_answer_resolution_to_disposition,
)
from src.audit_policy.models import (
    AuditTagPolicy,
    DispositionNode,
    ValidationPolicy,
)
from src.audit_policy.parser import parse_audit_project
from src.audit_policy.prompting_mapper import (
    map_prompting_answer_disposition,
)
from src.automation.decision import (
    decide_question_automation,
)
from src.evidence_quality.corroboration_models import (
    CorroboratedEvidenceResult,
)
from src.prompting.models import PromptingEvidence
from src.resolver.models import AnswerResolution


# Synthetic trees mirroring the Audit CRM answer-validation shapes.

def node(node_id, text, children=None, comments=False):
    return DispositionNode(
        id=node_id,
        text=text,
        comments_required=comments,
        children=children or [],
    )


MATCH_MISMATCH_TREE = [
    node(1, "Asked Right"),
    node(2, "Mismatch", comments=True),
    node(3, "Not Audible - No response"),
]

FLAT_PROMPTING_TREE = [
    node(10, "Yes - No Prompting Done"),
    node(11, "Mismatch", comments=True),
    node(12, "Not Audible - No response"),
    node(13, "Prompting -Party A"),
]

NESTED_PROMPTING_TREE = [
    node(20, "Not Audible - No response"),
    node(21, "Mismatch", comments=True),
    node(22, "Respondent answer without Prompting", [
        node(23, "Yes - No Prompting Done"),
        node(24, "Respondent says Party A"),
    ]),
    node(25, "Respondent answer after Prompting", [
        node(26, "Prompting -Party A"),
    ]),
]

INTRODUCTION_TREE = [
    node(30, "Yes - Perfect introduction"),
    node(31, "Not Audible - Agent did not ask the question"),
    node(32, "Incomplete Introduction"),
]


def tag_policy(answer_tree):
    return AuditTagPolicy(
        tag="q",
        placeholder="q",
        project_code="SAMPLE",
        active=True,
        order=1,
        tag_type="console",
        question_validation=ValidationPolicy(enabled=False),
        answer_validation=ValidationPolicy(
            enabled=True,
            dispositions=answer_tree,
        ),
    )


def resolution(status):
    return AnswerResolution(
        raw_text="x",
        resolved_option="A" if status != "UNCERTAIN" else None,
        stored_option="A" if status == "MATCH" else "B",
        status=status,
        confidence=1.0,
    )


def test_classifies_audit_crm_answer_tree_shapes():
    assert classify_answer_tree(MATCH_MISMATCH_TREE) == MATCH_MISMATCH
    assert classify_answer_tree(FLAT_PROMPTING_TREE) == FLAT_PROMPTING
    assert classify_answer_tree(NESTED_PROMPTING_TREE) == NESTED_PROMPTING
    assert classify_answer_tree(INTRODUCTION_TREE) == INTRODUCTION
    assert classify_answer_tree([node(40, "Something else")]) == UNSUPPORTED


def test_only_flat_prompting_trees_get_prompting_paths():
    assert answer_prompting_paths(FLAT_PROMPTING_TREE) == (
        ["Yes - No Prompting Done"],
        None,
    )
    for tree in (MATCH_MISMATCH_TREE, NESTED_PROMPTING_TREE, INTRODUCTION_TREE):
        assert answer_prompting_paths(tree) == (None, None)


def test_generic_mapper_does_not_suggest_mismatch_in_prompting_trees():
    for tree in (FLAT_PROMPTING_TREE, NESTED_PROMPTING_TREE, INTRODUCTION_TREE):
        suggestion = map_answer_resolution_to_disposition(
            resolution=resolution("MISMATCH"),
            tag_policy=tag_policy(tree),
        )

        assert suggestion.status == "NO_MAPPING"
        assert suggestion.disposition_id is None
        assert suggestion.review_required is True


def test_nested_tree_reports_pending_rule():
    suggestion = map_answer_resolution_to_disposition(
        resolution=resolution("MATCH"),
        tag_policy=tag_policy(NESTED_PROMPTING_TREE),
    )

    assert "pending confirmation" in suggestion.reason


def test_match_mismatch_tree_carries_comment_requirement():
    match = map_answer_resolution_to_disposition(
        resolution=resolution("MATCH"),
        tag_policy=tag_policy(MATCH_MISMATCH_TREE),
    )
    mismatch = map_answer_resolution_to_disposition(
        resolution=resolution("MISMATCH"),
        tag_policy=tag_policy(MATCH_MISMATCH_TREE),
    )

    assert match.disposition_text == "Asked Right"
    assert match.comments_required is False
    assert mismatch.disposition_text == "Mismatch"
    assert mismatch.comments_required is True
    assert mismatch.review_required is True


def prompting(status):
    return PromptingEvidence(
        status=status,
        confidence=0.95,
        agent_followup_text="",
        respondent_text="A",
        review_required=False,
        reason="synthetic",
    )


def test_flat_tree_maps_unprompted_match_to_no_prompting_done():
    suggestion = map_prompting_answer_disposition(
        resolution=resolution("MATCH"),
        prompting=prompting("NO_PROMPTING_EVIDENCE"),
        tag_policy=tag_policy(FLAT_PROMPTING_TREE),
        no_prompting_path=["Yes - No Prompting Done"],
        prompting_path=None,
    )

    assert suggestion.status == "SUGGESTED"
    assert suggestion.disposition_id == 10


def test_missing_prompted_path_leaves_prompted_answer_for_review():
    suggestion = map_prompting_answer_disposition(
        resolution=resolution("MATCH"),
        prompting=prompting("PROMPTING_EVIDENCE"),
        tag_policy=tag_policy(FLAT_PROMPTING_TREE),
        no_prompting_path=["Yes - No Prompting Done"],
        prompting_path=None,
    )

    assert suggestion.status == "NO_MAPPING"
    assert suggestion.disposition_id is None
    assert suggestion.review_required is True


def audit_result(answer_disposition, prompting_status=None):
    return QuestionAuditResult(
        question_key="q",
        evidence=QuestionEvidence(agent_text="question", respondent_text="answer"),
        resolved_option="A",
        stored_option="B",
        answer_resolution_status="MISMATCH",
        answer_resolution_confidence=1.0,
        prompting_status=prompting_status,
        answer_disposition=answer_disposition,
        review_required=False,
    )


def strong_evidence():
    return CorroboratedEvidenceResult(
        resolved_option="A",
        stored_option="B",
        resolution_status="MISMATCH",
        evidence_strength="STRONG",
        automation_status="AUTO_FILL_CANDIDATE",
        review_required=False,
    )


def answer_proposal(decision):
    return [p for p in decision.proposals if p.side == "answer"][0]


def test_comment_required_answer_is_never_auto_filled():
    decision = decide_question_automation(
        audit_result(
            SuggestedDisposition(
                disposition_id=2,
                disposition_text="Mismatch",
                disposition_path=["Mismatch"],
                comments_required=True,
            )
        ),
        strong_evidence(),
        require_question_disposition=False,
    )

    assert answer_proposal(decision).action == "PREFILL"
    assert "comment" in answer_proposal(decision).reason
    assert decision.action != "AUTO_FILL"


def test_parser_keeps_disposition_type():
    policy = parse_audit_project({
        "project_code": "SAMPLE",
        "project_tags": [{
            "tag": "remarks",
            "project_code": "SAMPLE",
            "is_active": 1,
            "desposition_type": "textbox",
            "desposition": {"question": {}, "primary_breakdown": []},
        }],
    })

    assert policy.tags["remarks"].disposition_type == "textbox"
