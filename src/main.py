import argparse
import json

from src.audit_policy.parser import load_audit_project
from src.domain.models import SurveyAuditRequest


def load_request(file_path: str) -> SurveyAuditRequest:
    with open(file_path, "r", encoding="utf-8") as file:
        payload = json.load(file)

    return SurveyAuditRequest.model_validate(payload)


def print_project_summary(
    request: SurveyAuditRequest,
    policy,
) -> None:
    if request.project_code != policy.project_code:
        raise ValueError(
            f"Project mismatch: request={request.project_code}, "
            f"policy={policy.project_code}"
        )

    console_tags = [
        tag
        for tag in policy.tags.values()
        if tag.tag_type == "console"
    ]

    local_tags = [
        tag
        for tag in policy.tags.values()
        if tag.tag_type == "local"
    ]

    matched_questions = []
    questions_without_audit_tag = []

    for question in request.questions:
        if question.key in policy.tags:
            matched_questions.append(question.key)
        else:
            questions_without_audit_tag.append(question.key)

    print()
    print("Survey Audio Intelligence")
    print("-------------------------")
    print(f"Response ID: {request.response_id}")
    print(f"Project: {policy.project_name}")
    print(f"Project Code: {policy.project_code}")
    print(f"Language: {request.language}")
    print()

    print(f"Active Audit Tags: {len(policy.tags)}")
    print(f"Console Tags: {len(console_tags)}")
    print(f"Local Tags: {len(local_tags)}")
    print()

    print(f"Survey Questions Received: {len(request.questions)}")
    print(f"Questions Matched To Audit Tags: {len(matched_questions)}")

    if matched_questions:
        print(
            "Matched:",
            ", ".join(matched_questions),
        )

    if questions_without_audit_tag:
        print(
            "No Active Audit Tag:",
            ", ".join(questions_without_audit_tag),
        )

    print()
    print("Foundation pipeline ready.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Survey Audio Intelligence prototype"
    )

    parser.add_argument(
        "--request",
        required=True,
        help="Path to survey audit request JSON",
    )

    parser.add_argument(
        "--policy",
        required=True,
        help="Path to Audit CRM project configuration JSON",
    )

    args = parser.parse_args()

    request = load_request(args.request)
    policy = load_audit_project(args.policy)

    print_project_summary(
        request=request,
        policy=policy,
    )


if __name__ == "__main__":
    main()