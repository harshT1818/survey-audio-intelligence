import argparse
import json
from pathlib import Path

from src.full_sample.evidence_diagnostics import (
    analyze_prompting_evaluation,
)
from src.full_sample.safe_prompting import (
    evaluate_prompting_dialogue_safe,
)
from src.full_sample.survey_options import (
    canonical_options_from_question,
    survey_question_map,
)


DEFAULT_TAGS = [
    "state_govt_change_party",
    "mla_choice",
    "cm_choice",
]


def load_json(
    path: Path,
):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--response-id",
        required=True,
    )

    parser.add_argument(
        "--tags",
        nargs="*",
        default=DEFAULT_TAGS,
    )

    args = parser.parse_args()

    sample_dir = (
        Path("data/private/r2")
        / args.response_id
    )

    dialogues = load_json(
        sample_dir
        / "prompting_dialogue_clean.json"
    )

    questions = load_json(
        sample_dir
        / "question_asr.json"
    )

    survey_definition = load_json(
        sample_dir
        / "survey_definition.json"
    )

    baseline = load_json(
        sample_dir
        / "prompting_benchmark.json"
    )

    dialogue_by_tag = {
        item["tag"]: item
        for item in dialogues
    }

    question_by_tag = {
        item["tag"]: item
        for item in questions
    }

    survey_by_tag = (
        survey_question_map(
            survey_definition
        )
    )

    baseline_by_tag = {
        item["tag"]: item
        for item in baseline
    }

    results = []

    print()
    print(
        "=== CLEAN SAFETY-AWARE "
        "PROMPTING BENCHMARK ==="
    )
    print()

    print(
        f"Response ID: "
        f"{args.response_id}"
    )

    print()

    for tag in args.tags:
        dialogue = (
            dialogue_by_tag.get(
                tag
            )
        )

        question = (
            question_by_tag.get(
                tag
            )
        )

        survey_question = (
            survey_by_tag.get(
                tag
            )
        )

        baseline_row = (
            baseline_by_tag.get(
                tag,
                {},
            )
        )

        if (
            dialogue is None
            or question is None
        ):
            print(
                f"{tag}: "
                f"MISSING CLEAN INPUT"
            )
            continue

        options = (
            canonical_options_from_question(
                survey_question
            )
        )

        evaluation = (
            evaluate_prompting_dialogue_safe(
                dialogue=dialogue,
                question_window=(
                    question
                ),
                options=options,
            )
        )

        do_not_read = (
            bool(
                survey_question.get(
                    "do_not_read_options",
                    False,
                )
            )
            if survey_question
            else False
        )

        diagnostics = (
            analyze_prompting_evaluation(
                evaluation=evaluation,
                options=options,
                stored_response=(
                    question.get(
                        "stored_response"
                    )
                ),
                do_not_read_options=(
                    do_not_read
                ),
            )
        )

        baseline_prediction = (
            baseline_row.get(
                "ai_prediction"
            )
            or baseline_row.get(
                "prediction"
            )
        )

        human_label = (
            baseline_row.get(
                "human_label"
            )
        )

        result = {
            "tag": tag,
            "human_label": (
                human_label
            ),
            "baseline_prediction": (
                baseline_prediction
            ),
            "clean_prediction": (
                evaluation[
                    "prediction"
                ]
            ),
            "raw_detector_prediction": (
                evaluation[
                    "raw_detector_prediction"
                ]
            ),
            "decision_safe": (
                evaluation[
                    "decision_safe"
                ]
            ),
            "reason": (
                evaluation[
                    "reason"
                ]
            ),
            "anchor_agent_turn": (
                evaluation[
                    "anchor_agent_turn"
                ]
            ),
            "initial_respondent_turn": (
                evaluation[
                    "initial_respondent_turn"
                ]
            ),
            "agent_followup_turns": (
                evaluation[
                    "agent_followup_turns"
                ]
            ),
            "rejected_respondent_turns": (
                evaluation[
                    "rejected_respondent_turns"
                ]
            ),
            "rejected_agent_followup_turns": (
                evaluation[
                    "rejected_agent_followup_turns"
                ]
            ),
            "diagnostics": (
                diagnostics
            ),
        }

        results.append(
            result
        )

        print(
            "=" * 90
        )

        print(tag)

        print(
            f"  Human:             "
            f"{human_label}"
        )

        print(
            f"  Baseline AI:       "
            f"{baseline_prediction}"
        )

        print(
            f"  Clean safe AI:     "
            f"{evaluation['prediction']}"
        )

        print(
            f"  Raw detector:      "
            f"{evaluation['raw_detector_prediction']}"
        )

        print(
            f"  Decision safe:     "
            f"{evaluation['decision_safe']}"
        )

        respondent = (
            evaluation[
                "initial_respondent_turn"
            ]
        )

        if respondent:
            print(
                "  Respondent:"
            )

            print(
                "    "
                f"{respondent.get('start_sec')}"
                "-"
                f"{respondent.get('end_sec')} "
                f"{respondent.get('transcript')}"
            )

        else:
            print(
                "  Respondent:         NONE"
            )

        rejected_r = (
            evaluation[
                "rejected_respondent_turns"
            ]
        )

        print(
            f"  Rejected R turns:  "
            f"{len(rejected_r)}"
        )

        for item in rejected_r:
            turn = item[
                "turn"
            ]

            print(
                "    - "
                f"{turn.get('start_sec')}"
                "-"
                f"{turn.get('end_sec')} "
                f"{item['reasons']} "
                f"| "
                f"{turn.get('transcript')}"
            )

        rejected_a = (
            evaluation[
                "rejected_agent_followup_turns"
            ]
        )

        print(
            f"  Rejected A turns:  "
            f"{len(rejected_a)}"
        )

        for item in rejected_a:
            turn = item[
                "turn"
            ]

            print(
                "    - "
                f"{turn.get('start_sec')}"
                "-"
                f"{turn.get('end_sec')} "
                f"{item['reasons']} "
                f"| "
                f"{turn.get('transcript')}"
            )

        print(
            f"  Safe followups:    "
            f"{len(evaluation['agent_followup_turns'])}"
        )

        print(
            f"  Diagnostic safety: "
            f"{diagnostics['evidence_safety']}"
        )

        flags = (
            diagnostics[
                "safety_flags"
            ]
        )

        print(
            f"  Flags:             "
            f"{flags or '-'}"
        )

        observations = (
            diagnostics[
                "observations"
            ]
        )

        print(
            f"  Observations:      "
            f"{observations or '-'}"
        )

        print(
            f"  Reason:            "
            f"{evaluation['reason']}"
        )

        print()

    output_path = (
        sample_dir
        / "prompting_benchmark_clean.json"
    )

    output_path.write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "=" * 90
    )

    print()

    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()