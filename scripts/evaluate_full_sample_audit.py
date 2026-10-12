import argparse
import json
from pathlib import Path

from src.audit_policy.parser import parse_audit_project
from src.full_sample.audit_runner import evaluate_full_sample


def main():
    parser = argparse.ArgumentParser(description="Evaluate prepared full-sample audit evidence offline.")
    parser.add_argument("--sample-dir", type=Path, required=True)
    parser.add_argument("--tags", nargs="+")
    parser.add_argument(
        "--prompting-aware-answers", action="store_true",
        help="Experimental: map unprompted matches on flat prompting trees "
             "to 'Yes - No Prompting Done' (prefill only).",
    )
    args = parser.parse_args()

    def load(name):
        return json.loads((args.sample_dir / name).read_text(encoding="utf-8-sig"))

    snapshot = load("audit_policy_snapshot.json")
    codes = {item["project_code"] for item in snapshot}
    if len(codes) != 1:
        raise ValueError("Policy snapshot must contain exactly one project.")
    policy = parse_audit_project({
        "project_code": codes.pop(), "project_tags": snapshot,
    }, active_only=False)
    report = evaluate_full_sample(
        dialogues=load("prompting_dialogue_clean.json"),
        windows=load("question_asr.json"),
        survey_definition=load("survey_definition.json"),
        policy=policy, human_audit=load("human_audit.json"), tags=args.tags,
        prompting_aware_answers=args.prompting_aware_answers,
    )
    output = args.sample_dir / "full_sample_audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
