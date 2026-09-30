import csv
from pathlib import Path

import pytest

from src.full_sample.survey_definition import (
    parse_survey_definition,
    parse_survey_definition_with_info,
    question_map,
)


HEADERS = [
    "Page ID",
    "Question ID",
    "Question Number",
    "Question Text",
    "Question Visible",
    "type",
    "tag",
    "Matrix Row",
    "Matrix Column",
    "dropdown Options",
    "Option Text",
    "file type",
    "Image URL",
    "Is Statement",
    "Has Comment",
    "Is Hidden",
    "Randomisation",
    "Skip To ID",
    "Skip to Question",
    "Option Details Count",
    "Hindi",
    "English",
    "Regional Language",
    "level",
    "VS_C_H",
    "LS_C_H",
    "Party",
    "DL",
    "Candidate ID",
    "EDM",
    "Alliance",
]


def write_file(
    path: Path,
    rows: list[dict],
    delimiter: str,
):
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=HEADERS,
            delimiter=delimiter,
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                row
            )


def basic_rows():
    return [
        {
            "Page ID": "page-1",
            "Question ID": "q-1",
            "Question Number": "1",
            "Question Text": (
                "क्या बदलाव चाहते हैं?"
            ),
            "Question Visible": "1",
            "type": "multiple",
            "tag": "change",
            "Option Text": "हाँ",
            "Hindi": "हाँ",
            "English": "Yes",
            "Regional Language": "हाँ",
            "Is Hidden": "0",
        },
        {
            "Question Text": (
                "क्या बदलाव चाहते हैं?"
            ),
            "Question Visible": "1",
            "type": "multiple",
            "tag": "change",
            "Option Text": "नहीं",
            "Hindi": "नहीं",
            "English": "No",
            "Regional Language": "नहीं",
            "Is Hidden": "0",
        },
    ]


def test_parses_tsv(
    tmp_path,
):
    path = (
        tmp_path
        / "survey.tsv"
    )

    write_file(
        path,
        basic_rows(),
        delimiter="\t",
    )

    questions, info = (
        parse_survey_definition_with_info(
            path
        )
    )

    by_tag = question_map(
        questions
    )

    assert (
        info.delimiter_name
        == "TSV"
    )

    assert (
        len(
            by_tag["change"].choices
        )
        == 2
    )


def test_parses_csv_even_when_named_tsv(
    tmp_path,
):
    path = (
        tmp_path
        / "survey.tsv"
    )

    write_file(
        path,
        basic_rows(),
        delimiter=",",
    )

    questions, info = (
        parse_survey_definition_with_info(
            path
        )
    )

    by_tag = question_map(
        questions
    )

    assert (
        info.delimiter_name
        == "CSV"
    )

    assert (
        len(
            by_tag["change"].choices
        )
        == 2
    )


def test_parses_static_choices(
    tmp_path,
):
    path = (
        tmp_path
        / "survey.csv"
    )

    write_file(
        path,
        basic_rows(),
        delimiter=",",
    )

    questions = (
        parse_survey_definition(
            path
        )
    )

    by_tag = question_map(
        questions
    )

    question = by_tag[
        "change"
    ]

    assert (
        question.question_id
        == "q-1"
    )

    assert (
        len(
            question.choices
        )
        == 2
    )

    assert (
        question.choice_catalog_status
        == "STATIC"
    )

    assert (
        question.resolution_ready
        is True
    )


def test_preserves_choice_metadata(
    tmp_path,
):
    path = (
        tmp_path
        / "survey.csv"
    )

    write_file(
        path,
        [
            {
                "Page ID": "page-1",
                "Question ID": "q-1",
                "Question Number": "1",
                "Question Text": (
                    "Candidate?"
                ),
                "Question Visible": "1",
                "type": "multiple",
                "tag": "candidate",
                "Option Text": (
                    "Candidate A [Party]"
                ),
                "Hindi": (
                    "कैंडिडेट ए [पार्टी]"
                ),
                "English": (
                    "Candidate A [Party]"
                ),
                "Regional Language": (
                    "कैंडिडेट ए"
                ),
                "Party": "BSP",
                "DL": "BSP",
                "Candidate ID": (
                    "candidate-123"
                ),
                "Randomisation": "1",
            }
        ],
        delimiter=",",
    )

    question = question_map(
        parse_survey_definition(
            path
        )
    )["candidate"]

    choice = question.choices[
        0
    ]

    assert (
        choice.party
        == "BSP"
    )

    assert (
        choice.dl
        == "BSP"
    )

    assert (
        choice.candidate_id
        == "candidate-123"
    )

    assert (
        choice.randomisation
        is True
    )


def test_detects_do_not_read_options(
    tmp_path,
):
    path = (
        tmp_path
        / "survey.csv"
    )

    write_file(
        path,
        [
            {
                "Question ID": "q-1",
                "Question Text": (
                    "किसे चुनेंगे? "
                    "DO NOT READ THE OPTIONS"
                ),
                "Question Visible": "1",
                "type": "multiple",
                "tag": "choice",
                "Option Text": "A",
                "Hindi": "A",
                "English": "A",
                "Regional Language": "A",
            }
        ],
        delimiter=",",
    )

    question = question_map(
        parse_survey_definition(
            path
        )
    )["choice"]

    assert (
        question.do_not_read_options
        is True
    )


def test_detects_do_not_read_without_space(
    tmp_path,
):
    path = (
        tmp_path
        / "survey.csv"
    )

    write_file(
        path,
        [
            {
                "Question ID": "q-1",
                "Question Text": (
                    "किसे चुनेंगे? "
                    "DO NOTREAD THE OPTIONS"
                ),
                "Question Visible": "1",
                "type": "multiple",
                "tag": "choice",
                "Option Text": "A",
                "Hindi": "A",
                "English": "A",
                "Regional Language": "A",
            }
        ],
        delimiter=",",
    )

    question = question_map(
        parse_survey_definition(
            path
        )
    )["choice"]

    assert (
        question.do_not_read_options
        is True
    )


def test_detects_dynamic_placeholder(
    tmp_path,
):
    path = (
        tmp_path
        / "survey.csv"
    )

    write_file(
        path,
        [
            {
                "Question ID": "q-2",
                "Question Text": (
                    "अगर $#mla_choice-Hindi "
                    "उपलब्ध नहीं हैं?"
                ),
                "Question Visible": "1",
                "type": "multiple",
                "tag": (
                    "second_mla_choice_new"
                ),
                "Option Text": "1",
                "Hindi": "1",
                "English": "1",
                "Regional Language": "1",
                "Is Hidden": "1",
            }
        ],
        delimiter=",",
    )

    question = question_map(
        parse_survey_definition(
            path
        )
    )[
        "second_mla_choice_new"
    ]

    assert (
        question.choice_catalog_status
        == "DYNAMIC_PLACEHOLDER"
    )

    assert (
        question.resolution_ready
        is False
    )

    assert (
        len(
            question.dynamic_dependencies
        )
        == 1
    )

    dependency = (
        question
        .dynamic_dependencies[0]
    )

    assert (
        dependency.tag
        == "mla_choice"
    )

    assert (
        dependency.field
        == "Hindi"
    )


def test_duplicate_question_ids_for_tag_fail(
    tmp_path,
):
    path = (
        tmp_path
        / "survey.csv"
    )

    write_file(
        path,
        [
            {
                "Question ID": "q-1",
                "Question Text": "Question",
                "Question Visible": "1",
                "type": "multiple",
                "tag": "same_tag",
                "Option Text": "A",
                "Hindi": "A",
                "English": "A",
                "Regional Language": "A",
            },
            {
                "Question ID": "q-2",
                "Question Text": "Question",
                "Question Visible": "1",
                "type": "multiple",
                "tag": "same_tag",
                "Option Text": "B",
                "Hindi": "B",
                "English": "B",
                "Regional Language": "B",
            },
        ],
        delimiter=",",
    )

    with pytest.raises(
        ValueError
    ):
        parse_survey_definition(
            path
        )