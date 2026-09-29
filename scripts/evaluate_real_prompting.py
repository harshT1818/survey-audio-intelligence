import argparse
import json
from pathlib import Path

from src.full_sample.prompting_benchmark import (
    compare_prompting_prediction,
    evaluate_prompting_dialogue,
    extract_canonical_options,
    find_policy_entry,
    infer_human_prompting_label,
)


DEFAULT_TAGS = [
    "state_govt_change",
    "state_govt_change_party",
    "mla_choice",
    "second_mla_choice_new",
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


def shorten(
    text: str,
    maximum: int = 100,
) -> str:
    text = " ".join(
        str(text).split()
    )

    if len(text) <= maximum:
        return text

    return (
        text[:maximum - 3]
        + "..."
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
        / "prompting_dialogue.json"
    )

    question_asr = load_json(
        sample_dir
        / "question_asr.json"
    )

    policy = load_json(
        sample_dir
        / "audit_policy_snapshot.json"
    )

    human_audit = load_json(
        sample_dir
        / "human_audit.json"
    )

    dialogue_by_tag = {
        item["tag"]: item
        for item in dialogues
    }

    question_by_tag = {
        item["tag"]: item
        for item in question_asr
    }

    results = []

    print()
    print(
        "=== REAL PROMPTING "
        "BENCHMARK ==="
    )
    print()

    print(
        f"Response ID: "
        f"{args.response_id}"
    )

    print(
        f"Questions:   "
        f"{len(args.tags)}"
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

        if (
            dialogue is None
            or question is None
        ):
            print(
                f"WARNING: missing "
                f"data for {tag}"
            )
            continue

        policy_entry = (
            find_policy_entry(
                policy,
                tag,
            )
        )

        options = (
            extract_canonical_options(
                policy_entry
            )
        )

        human_payload = (
            human_audit.get(
                tag
            )
        )

        human_label = (
            infer_human_prompting_label(
                human_payload
            )
        )

        evaluation = (
            evaluate_prompting_dialogue(
                dialogue=dialogue,
                question_window=(
                    question
                ),
                options=options,
            )
        )

        prediction = (
            evaluation[
                "prediction"
            ]
        )

        agreement = (
            compare_prompting_prediction(
                prediction=prediction,
                human_label=human_label,
            )
        )

        detector_result = (
            evaluation.get(
                "detector_result"
            )
        )

        record = {
            "tag": tag,
            "stored_response": (
                question.get(
                    "stored_response"
                )
            ),
            "human_label": (
                human_label
            ),
            "ai_prediction": (
                prediction
            ),
            "agreement": (
                agreement
            ),
            "review_required": (
                evaluation[
                    "review_required"
                ]
            ),
            "option_count": len(
                options
            ),
            "options": [
                option.model_dump()
                for option in options
            ],
            "reason": (
                evaluation["reason"]
            ),
            "detector_result": (
                detector_result
            ),
            "anchor_agent_turn": (
                evaluation.get(
                    "anchor_agent_turn"
                )
            ),
            "initial_respondent_turn": (
                evaluation.get(
                    "initial_respondent_turn"
                )
            ),
            "agent_followup_turns": (
                evaluation.get(
                    "agent_followup_turns",
                    [],
                )
            ),
        }

        results.append(
            record
        )

        print(
            "=" * 90
        )

        print(tag)

        print(
            f"  Human:      "
            f"{human_label}"
        )

        print(
            f"  AI:         "
            f"{prediction}"
        )

        print(
            f"  Agreement:  "
            f"{agreement}"
        )

        print(
            f"  Options:    "
            f"{len(options)}"
        )

        initial = (
            evaluation.get(
                "initial_respondent_turn"
            )
        )

        if initial:
            print(
                f"  Respondent: "
                f"{shorten(initial.get('transcript', ''))}"
            )

        followups = (
            evaluation.get(
                "agent_followup_turns",
                []
            )
        )

        if followups:
            followup_text = " ".join(
                str(
                    turn.get(
                        "transcript",
                        "",
                    )
                )
                for turn in followups
            )

            print(
                f"  Follow-up:  "
                f"{shorten(followup_text)}"
            )

        print(
            f"  Reason:     "
            f"{evaluation['reason']}"
        )

        print()

    output_path = (
        sample_dir
        / "prompting_benchmark.json"
    )

    output_path.write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    resolved = [
        row
        for row in results
        if row[
            "ai_prediction"
        ]
        in {
            "PROMPTING",
            "NO_PROMPTING",
        }
    ]

    agreements = [
        row
        for row in resolved
        if row["agreement"]
        is True
    ]

    disagreements = [
        row
        for row in resolved
        if row["agreement"]
        is False
    ]

    uncertain = [
        row
        for row in results
        if row[
            "ai_prediction"
        ]
        == "UNCERTAIN"
    ]

    insufficient = [
        row
        for row in results
        if row[
            "ai_prediction"
        ]
        == (
            "INSUFFICIENT_ROLE_EVIDENCE"
        )
    ]

    print(
        "=" * 90
    )

    print()
    print(
        "=== BENCHMARK SUMMARY ==="
    )
    print()

    print(
        f"Total:             "
        f"{len(results)}"
    )

    print(
        f"Resolved AI:       "
        f"{len(resolved)}"
    )

    print(
        f"Agreements:        "
        f"{len(agreements)}"
    )

    print(
        f"Disagreements:     "
        f"{len(disagreements)}"
    )

    print(
        f"Uncertain:         "
        f"{len(uncertain)}"
    )

    print(
        f"Insufficient:      "
        f"{len(insufficient)}"
    )

    if resolved:
        agreement_rate = (
            len(agreements)
            / len(resolved)
            * 100
        )

        print(
            f"Resolved agreement:"
            f" "
            f"{agreement_rate:.1f}%"
        )

    print()
    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()