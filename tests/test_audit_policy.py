from src.audit_policy.parser import load_audit_project


def test_active_tags_are_loaded():
    policy = load_audit_project("configs/sample_audit_project.json")

    assert "ac_name" in policy.tags
    assert "state_govt_change" in policy.tags
    assert "group_interview" in policy.tags


def test_inactive_tags_are_excluded():
    policy = load_audit_project("configs/sample_audit_project.json")

    assert "inactive_example" not in policy.tags


def test_question_and_answer_validation_are_preserved():
    policy = load_audit_project("configs/sample_audit_project.json")

    tag = policy.tags["state_govt_change"]

    assert tag.question_validation.enabled is True
    assert tag.answer_validation.enabled is True


def test_nested_dispositions_are_preserved():
    policy = load_audit_project("configs/sample_audit_project.json")

    tag = policy.tags["state_govt_change"]

    parent = tag.answer_validation.dispositions[0]

    assert parent.text == "Respondent answer without Prompting"

    child_texts = [child.text for child in parent.children]

    assert "Yes - No Prompting Done" in child_texts
    assert "Respondent says Option A" in child_texts
    assert "Respondent says Option B" in child_texts


def test_comment_requirement_is_preserved():
    policy = load_audit_project("configs/sample_audit_project.json")

    tag = policy.tags["state_govt_change"]

    mismatch = next(
        disposition
        for disposition in tag.answer_validation.dispositions
        if disposition.text == "Mismatch"
    )

    assert mismatch.comments_required is True


def test_local_tag_type_is_preserved():
    policy = load_audit_project("configs/sample_audit_project.json")

    tag = policy.tags["group_interview"]

    assert tag.tag_type == "local"