import json
from pathlib import Path

from src.audit_engine.question_audit import audit_question
from src.audit_policy.models import (
    AuditTagPolicy,
    DispositionNode,
    ValidationPolicy,
)
from src.dialogue.models import QuestionDialogue
from src.domain.models import SurveyQuestion
from src.evaluation.models import (
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationFixture,
    EvaluationSummary,
)


def load_evaluation_fixture(
    file_path: str | Path,
) -> EvaluationFixture:
    file_path = Path(file_path)

    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    return EvaluationFixture.model_validate(
        payload
    )


def _make_policy(
    case: EvaluationCase,
) -> AuditTagPolicy:

    question_dispositions = [
        DispositionNode(
            id=1001,
            text="Asked Right",
            children=[],
        ),
    ]

    if case.prompting_aware:
        answer_dispositions = [
            DispositionNode(
                id=2000,
                text="Respondent answer without Prompting",
                children=[
                    DispositionNode(
                        id=2001,
                        text=(
                            case.no_prompting_path[-1]
                            if case.no_prompting_path
                            else "No Prompting"
                        ),
                        children=[],
                    ),
                ],
            ),
            DispositionNode(
                id=3000,
                text="Respondent answer after Prompting",
                children=[
                    DispositionNode(
                        id=3001,
                        text=(
                            case.prompting_path[-1]
                            if case.prompting_path
                            else "Prompting Done"
                        ),
                        children=[],
                    ),
                ],
            ),
        ]

    else:
        answer_dispositions = [
            DispositionNode(
                id=4001,
                text="Asked Right",
                children=[],
            ),
            DispositionNode(
                id=4002,
                text="Mismatch",
                children=[],
            ),
        ]

    return AuditTagPolicy(
        tag=case.question_key,
        placeholder=case.question_key,
        project_code="EVALUATION",
        active=True,
        order=1,
        tag_type="console",
        question_tag_id=1,

        question_validation=ValidationPolicy(
            enabled=True,
            validation_type="single",
            dispositions=question_dispositions,
        ),

        answer_validation=ValidationPolicy(
            enabled=True,
            validation_type="single",
            dispositions=answer_dispositions,
        ),
    )


def _compare_result(
    case: EvaluationCase,
    actual,
) -> list[str]:

    failures: list[str] = []

    checks = {
        "question_validation_status": (
            actual.question_validation_status
        ),
        "answer_resolution_status": (
            actual.answer_resolution_status
        ),
        "resolved_option": (
            actual.resolved_option
        ),
        "prompting_status": (
            actual.prompting_status
        ),
        "answer_disposition_text": (
            actual.answer_disposition.disposition_text
            if actual.answer_disposition
            else None
        ),
        "review_required": (
            actual.review_required
        ),
    }

    expected = case.expected.model_dump()

    for field_name, actual_value in checks.items():
        expected_value = expected[field_name]

        if actual_value != expected_value:
            failures.append(
                f"{field_name}: "
                f"expected={expected_value!r}, "
                f"actual={actual_value!r}"
            )

    return failures


def run_evaluation_case(
    case: EvaluationCase,
) -> EvaluationCaseResult:

    question = SurveyQuestion(
        key=case.question_key,
        text_hi=case.question_text_hi,
        type=case.question_type,
        options=[],
        selected_answer=case.stored_answer,
    )

    dialogue = QuestionDialogue(
        turns=case.turns
    )

    policy = _make_policy(
        case
    )

    result = audit_question(
        question=question,
        dialogue=dialogue,
        canonical_options=case.options,
        tag_policy=policy,
        no_prompting_path=(
            case.no_prompting_path
            if case.prompting_aware
            else None
        ),
        prompting_path=(
            case.prompting_path
            if case.prompting_aware
            else None
        ),
    )

    failures = _compare_result(
        case=case,
        actual=result,
    )

    return EvaluationCaseResult(
        case_id=case.case_id,
        passed=not failures,
        expected=case.expected,
        actual=result.model_dump(),
        failures=failures,
    )


def run_evaluation_fixture(
    fixture: EvaluationFixture,
) -> EvaluationSummary:

    results = [
        run_evaluation_case(case)
        for case in fixture.cases
    ]

    passed_cases = sum(
        result.passed
        for result in results
    )

    return EvaluationSummary(
        fixture_name=fixture.fixture_name,
        total_cases=len(results),
        passed_cases=passed_cases,
        failed_cases=(
            len(results) - passed_cases
        ),
        results=results,
    )