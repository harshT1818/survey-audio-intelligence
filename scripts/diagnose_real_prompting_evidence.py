import argparse
import json
from pathlib import Path

from src.full_sample.evidence_diagnostics import (
    analyze_prompting_evaluation,
)
from src.full_sample.prompting_benchmark import (
    evaluate_prompting_dialogue,
)
from src.full_sample.survey_options import (
    canonical_options_from_question,
    survey_question_map,
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

    survey_definition = load_json(
        sample_dir
        / "survey_definition.json"
    )

    dialogue_by_tag = {
        item["tag"]: item
        for item in dialogues
    }

    question_by_tag = {
        item["tag"]: item
        for item in question_asr
    }

    survey_by_tag = (
        survey_question_map(
            survey_definition
        )
    )

    results = []

    print()
    print(
        "=== DECISION-LOCAL "
        "PROMPTING DIAGNOSTICS ==="
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

        survey_question = (
            survey_by_tag.get(
                tag
            )
        )

        if (
            dialogue is None
            or question is None
        ):
            print(
                f"{tag}: "
                f"MISSING INPUT"
            )
            continue

        options = (
            canonical_options_from_question(
                survey_question
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

        evaluation = (
            evaluate_prompting_dialogue(
                dialogue=dialogue,
                question_window=(
                    question
                ),
                options=options,
            )
        )

        analysis = (
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

        result = {
            "tag": tag,
            "prediction": (
                evaluation[
                    "prediction"
                ]
            ),
            "option_count": (
                len(options)
            ),
            "do_not_read_options": (
                do_not_read
            ),
            **analysis,
        }

        results.append(
            result
        )

        print(
            "=" * 90
        )

        print(tag)

        print(
            f"  Prediction:       "
            f"{evaluation['prediction']}"
        )

        print(
            f"  Safety:           "
            f"{analysis['evidence_safety']}"
        )

        print(
            f"  Anchor method:    "
            f"{analysis['anchor_method']}"
        )

        print(
            f"  Anchor similarity:"
            f" "
            f"{analysis['anchor_similarity']}"
        )

        anchor = (
            analysis[
                "anchor_agent_turn"
            ]
        )

        if anchor:
            print(
                "  Anchor:"
            )

            print(
                "    "
                f"{anchor.get('start_sec')}"
                "-"
                f"{anchor.get('end_sec')} "
                f"{anchor.get('transcript')}"
            )

        respondent = (
            analysis[
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
                "  Respondent:       NONE"
            )

        flags = (
            analysis[
                "safety_flags"
            ]
        )

        if flags:
            print(
                "  Safety flags:"
            )

            for flag in flags:
                print(
                    f"    - {flag}"
                )

        else:
            print(
                "  Safety flags:     -"
            )

        observations = (
            analysis[
                "observations"
            ]
        )

        if observations:
            print(
                "  Observations:"
            )

            for observation in (
                observations
            ):
                print(
                    f"    - {observation}"
                )

        else:
            print(
                "  Observations:     -"
            )

        conflicts = (
            analysis[
                "role_conflicts"
            ]
        )

        if conflicts:
            print(
                "  Role conflicts:"
            )

            for conflict in conflicts:
                print(
                    "    - "
                    f"{conflict.get('start_sec')}"
                    "-"
                    f"{conflict.get('end_sec')} "
                    f"{conflict.get('transcript')}"
                )

        selected = (
            analysis[
                "selected_option_match"
            ]
        )

        print(
            "  Stored resolved:  "
            f"{selected is not None}"
        )

        if selected:
            print(
                "  Stored option:    "
                f"{selected['option_value']}"
            )

        print(
            "  Agent selected "
            "mentions: "
            f"{len(analysis['selected_agent_mentions'])}"
        )

        print(
            "  Distinct agent "
            "options:  "
            f"{analysis['distinct_agent_option_count']}"
        )

        print()

    output_path = (
        sample_dir
        / (
            "prompting_evidence_"
            "diagnostics.json"
        )
    )

    output_path.write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    safe = [
        item
        for item in results
        if item[
            "evidence_safety"
        ]
        == "SAFE_FOR_PROMPTING_RULES"
    ]

    review = [
        item
        for item in results
        if item[
            "evidence_safety"
        ]
        == "REVIEW"
    ]

    print(
        "=" * 90
    )

    print()
    print(
        "=== DIAGNOSTIC SUMMARY ==="
    )
    print()

    print(
        f"Total:   "
        f"{len(results)}"
    )

    print(
        f"Safe:    "
        f"{len(safe)}"
    )

    print(
        f"Review:  "
        f"{len(review)}"
    )

    print()
    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()