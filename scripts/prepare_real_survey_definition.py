import argparse
import json
from pathlib import Path

from src.full_sample.survey_definition import (
    parse_survey_definition_with_info,
    question_map,
)


DEFAULT_TAGS = [
    "state_govt_change",
    "state_govt_change_party",
    "mla_choice",
    "second_mla_choice_new",
    "cm_choice",
]


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--response-id",
        required=True,
    )

    parser.add_argument(
        "--input",
        default=None,
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

    input_path = (
        Path(
            args.input
        )
        if args.input
        else (
            sample_dir
            / "survey_definition.tsv"
        )
    )

    (
        questions,
        load_info,
    ) = (
        parse_survey_definition_with_info(
            input_path
        )
    )

    by_tag = question_map(
        questions
    )

    output_path = (
        sample_dir
        / "survey_definition.json"
    )

    payload = {
        "response_id": (
            args.response_id
        ),
        "source_file": (
            input_path.name
        ),
        "source_format": (
            load_info.delimiter_name
        ),
        "source_encoding": (
            load_info.encoding
        ),
        "question_count": (
            len(questions)
        ),
        "questions": [
            question.model_dump()
            for question in questions
        ],
    }

    output_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "=== SURVEYXPress "
        "DEFINITION ==="
    )
    print()

    print(
        f"Input:      "
        f"{input_path}"
    )

    print(
        f"Format:     "
        f"{load_info.delimiter_name}"
    )

    print(
        f"Encoding:   "
        f"{load_info.encoding}"
    )

    print(
        f"Questions:  "
        f"{len(questions)}"
    )

    print()

    for tag in args.tags:
        question = by_tag.get(
            tag
        )

        if question is None:
            print(
                f"{tag:<30} "
                f"MISSING"
            )
            continue

        dependencies = (
            ", ".join(
                (
                    f"{item.tag}"
                    f"-{item.field}"
                )
                for item
                in question
                .dynamic_dependencies
            )
            or "-"
        )

        print(
            f"{tag:<30} "
            f"choices="
            f"{len(question.choices):<3} "
            f"catalog="
            f"{question.choice_catalog_status:<20} "
            f"ready="
            f"{str(question.resolution_ready):<5} "
            f"do_not_read="
            f"{str(question.do_not_read_options):<5} "
            f"depends="
            f"{dependencies}"
        )

    print()
    print(
        f"Saved: "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()