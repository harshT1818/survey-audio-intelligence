import csv
import io
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel


DYNAMIC_REFERENCE_PATTERN = re.compile(
    r"\$#([A-Za-z0-9_]+)-([A-Za-z0-9_]+)"
)

DO_NOT_READ_PATTERN = re.compile(
    r"DO\s*NOT\s*READ\s*THE\s*OPTIONS",
    flags=re.IGNORECASE,
)


REQUIRED_COLUMNS = {
    "Question ID",
    "Question Text",
    "Question Visible",
    "type",
    "tag",
    "Option Text",
    "Hindi",
    "English",
    "Regional Language",
}


SUPPORTED_ENCODINGS = [
    "utf-8-sig",
    "utf-8",
    "utf-16",
    "utf-16-le",
    "utf-16-be",
]


class DynamicReference(BaseModel):
    tag: str
    field: str


class SurveyChoiceDefinition(BaseModel):
    option_text: str

    hindi: str | None = None
    english: str | None = None
    regional_language: str | None = None

    dropdown_options: str | None = None
    file_type: str | None = None
    image_url: str | None = None

    is_statement: bool | None = None
    has_comment: bool | None = None
    is_hidden: bool | None = None
    randomisation: bool | None = None

    skip_to_id: str | None = None
    skip_to_question: str | None = None

    option_details_count: int | None = None

    level: str | None = None
    vs_c_h: str | None = None
    ls_c_h: str | None = None

    party: str | None = None
    dl: str | None = None
    candidate_id: str | None = None
    edm: str | None = None
    alliance: str | None = None


class SurveyQuestionDefinition(BaseModel):
    page_id: str | None = None
    question_id: str | None = None
    question_number: str | None = None

    question_text: str
    question_visible: bool | None = None
    question_type: str
    tag: str

    matrix_row: str | None = None
    matrix_column: str | None = None

    do_not_read_options: bool = False

    dynamic_dependencies: list[
        DynamicReference
    ]

    choice_catalog_status: str
    resolution_ready: bool

    choices: list[
        SurveyChoiceDefinition
    ]


class SurveyDefinitionLoadInfo(BaseModel):
    encoding: str
    delimiter: str
    delimiter_name: str
    headers: list[str]


def clean(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(
        value
    ).strip()

    return text or None


def parse_bool(
    value: Any,
) -> bool | None:
    text = clean(
        value
    )

    if text is None:
        return None

    normalized = text.lower()

    if normalized in {
        "1",
        "true",
        "yes",
    }:
        return True

    if normalized in {
        "0",
        "false",
        "no",
    }:
        return False

    return None


def parse_int(
    value: Any,
) -> int | None:
    text = clean(
        value
    )

    if text is None:
        return None

    try:
        return int(
            float(text)
        )
    except ValueError:
        return None


def first_non_empty(
    rows: list[dict[str, Any]],
    key: str,
) -> str | None:
    for row in rows:
        value = clean(
            row.get(
                key
            )
        )

        if value is not None:
            return value

    return None


def decode_file(
    path: Path,
) -> tuple[str, str]:
    raw = path.read_bytes()

    last_error = None

    for encoding in SUPPORTED_ENCODINGS:
        try:
            text = raw.decode(
                encoding
            )

            if text.strip():
                return (
                    text,
                    encoding,
                )

        except UnicodeDecodeError as exc:
            last_error = exc

    raise ValueError(
        "Could not decode survey "
        f"definition file: {path}. "
        f"Last error: {last_error}"
    )


def normalize_header(
    value: str,
) -> str:
    return (
        value
        .replace("\ufeff", "")
        .strip()
    )


def detect_delimiter(
    text: str,
) -> str:
    """
    Detect CSV vs TSV independently of file extension.

    SurveyXpress exports may be downloaded as comma-separated
    CSV even when the local file is named .tsv.
    """
    lines = [
        line
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        raise ValueError(
            "Survey definition is empty."
        )

    sample = "\n".join(
        lines[:20]
    )

    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=",\t;",
        )

        return dialect.delimiter

    except csv.Error:
        first_line = lines[0]

        counts = {
            ",": first_line.count(
                ","
            ),
            "\t": first_line.count(
                "\t"
            ),
            ";": first_line.count(
                ";"
            ),
        }

        delimiter = max(
            counts,
            key=counts.get,
        )

        if counts[
            delimiter
        ] == 0:
            raise ValueError(
                "Could not detect delimiter "
                "for survey definition."
            )

        return delimiter


def delimiter_name(
    delimiter: str,
) -> str:
    if delimiter == ",":
        return "CSV"

    if delimiter == "\t":
        return "TSV"

    if delimiter == ";":
        return "SEMICOLON"

    return repr(
        delimiter
    )


def load_rows(
    path: Path,
) -> tuple[
    list[dict[str, Any]],
    SurveyDefinitionLoadInfo,
]:
    if not path.exists():
        raise FileNotFoundError(
            "Survey definition not found: "
            f"{path}"
        )

    text, encoding = decode_file(
        path
    )

    delimiter = detect_delimiter(
        text
    )

    handle = io.StringIO(
        text,
        newline="",
    )

    reader = csv.DictReader(
        handle,
        delimiter=delimiter,
    )

    if reader.fieldnames is None:
        raise ValueError(
            "Survey definition has no header."
        )

    raw_headers = list(
        reader.fieldnames
    )

    normalized_headers = [
        normalize_header(
            header
        )
        for header in raw_headers
    ]

    reader.fieldnames = (
        normalized_headers
    )

    missing = (
        REQUIRED_COLUMNS
        - set(
            normalized_headers
        )
    )

    if missing:
        raise ValueError(
            "Survey definition is missing "
            "required columns: "
            + ", ".join(
                sorted(
                    missing
                )
            )
            + ". "
            + "Detected format="
            + delimiter_name(
                delimiter
            )
            + ", encoding="
            + encoding
            + ". Headers found: "
            + repr(
                normalized_headers
            )
        )

    rows = []

    for row in reader:
        normalized_row = {}

        for key, value in row.items():
            if key is None:
                continue

            normalized_key = (
                normalize_header(
                    key
                )
            )

            normalized_row[
                normalized_key
            ] = value

        rows.append(
            normalized_row
        )

    info = (
        SurveyDefinitionLoadInfo(
            encoding=encoding,
            delimiter=delimiter,
            delimiter_name=(
                delimiter_name(
                    delimiter
                )
            ),
            headers=(
                normalized_headers
            ),
        )
    )

    return (
        rows,
        info,
    )


def extract_dynamic_references(
    question_text: str,
) -> list[DynamicReference]:
    references = []

    seen = set()

    for tag, field in (
        DYNAMIC_REFERENCE_PATTERN.findall(
            question_text
        )
    ):
        key = (
            tag,
            field,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        references.append(
            DynamicReference(
                tag=tag,
                field=field,
            )
        )

    return references


def build_choice(
    row: dict[str, Any],
) -> SurveyChoiceDefinition | None:
    option_text = clean(
        row.get(
            "Option Text"
        )
    )

    if option_text is None:
        return None

    return SurveyChoiceDefinition(
        option_text=option_text,
        hindi=clean(
            row.get(
                "Hindi"
            )
        ),
        english=clean(
            row.get(
                "English"
            )
        ),
        regional_language=clean(
            row.get(
                "Regional Language"
            )
        ),
        dropdown_options=clean(
            row.get(
                "dropdown Options"
            )
        ),
        file_type=clean(
            row.get(
                "file type"
            )
        ),
        image_url=clean(
            row.get(
                "Image URL"
            )
        ),
        is_statement=parse_bool(
            row.get(
                "Is Statement"
            )
        ),
        has_comment=parse_bool(
            row.get(
                "Has Comment"
            )
        ),
        is_hidden=parse_bool(
            row.get(
                "Is Hidden"
            )
        ),
        randomisation=parse_bool(
            row.get(
                "Randomisation"
            )
        ),
        skip_to_id=clean(
            row.get(
                "Skip To ID"
            )
        ),
        skip_to_question=clean(
            row.get(
                "Skip to Question"
            )
        ),
        option_details_count=(
            parse_int(
                row.get(
                    "Option Details Count"
                )
            )
        ),
        level=clean(
            row.get(
                "level"
            )
        ),
        vs_c_h=clean(
            row.get(
                "VS_C_H"
            )
        ),
        ls_c_h=clean(
            row.get(
                "LS_C_H"
            )
        ),
        party=clean(
            row.get(
                "Party"
            )
        ),
        dl=clean(
            row.get(
                "DL"
            )
        ),
        candidate_id=clean(
            row.get(
                "Candidate ID"
            )
        ),
        edm=clean(
            row.get(
                "EDM"
            )
        ),
        alliance=clean(
            row.get(
                "Alliance"
            )
        ),
    )


def choice_identity(
    choice: SurveyChoiceDefinition,
) -> tuple:
    return (
        choice.option_text,
        choice.hindi,
        choice.english,
        choice.regional_language,
        choice.party,
        choice.dl,
        choice.candidate_id,
    )


def classify_choice_catalog(
    question_type: str,
    choices: list[
        SurveyChoiceDefinition
    ],
    dependencies: list[
        DynamicReference
    ],
) -> tuple[str, bool]:
    normalized_type = (
        question_type
        .strip()
        .lower()
    )

    if not choices:
        return (
            "NO_STATIC_CHOICES",
            False,
        )

    option_values = {
        choice.option_text.strip()
        for choice in choices
    }

    placeholder_values = {
        "0",
        "1",
    }

    looks_like_placeholder = (
        len(option_values) <= 1
        and option_values.issubset(
            placeholder_values
        )
    )

    if (
        dependencies
        and looks_like_placeholder
    ):
        return (
            "DYNAMIC_PLACEHOLDER",
            False,
        )

    if normalized_type in {
        "subjective",
        "blank",
    }:
        return (
            "NO_STATIC_CHOICES",
            False,
        )

    return (
        "STATIC",
        True,
    )


def build_question(
    tag: str,
    rows: list[
        dict[str, Any]
    ],
) -> SurveyQuestionDefinition:
    question_ids = {
        clean(
            row.get(
                "Question ID"
            )
        )
        for row in rows
        if clean(
            row.get(
                "Question ID"
            )
        )
    }

    if len(
        question_ids
    ) > 1:
        raise ValueError(
            "The same tag maps to multiple "
            "question IDs: "
            f"{tag} -> "
            f"{sorted(question_ids)}"
        )

    question_text = (
        first_non_empty(
            rows,
            "Question Text",
        )
        or ""
    )

    question_type = (
        first_non_empty(
            rows,
            "type",
        )
        or ""
    )

    dependencies = (
        extract_dynamic_references(
            question_text
        )
    )

    choices = []

    seen_choices = set()

    for row in rows:
        choice = build_choice(
            row
        )

        if choice is None:
            continue

        identity = choice_identity(
            choice
        )

        if identity in seen_choices:
            continue

        seen_choices.add(
            identity
        )

        choices.append(
            choice
        )

    (
        catalog_status,
        resolution_ready,
    ) = classify_choice_catalog(
        question_type=question_type,
        choices=choices,
        dependencies=dependencies,
    )

    return SurveyQuestionDefinition(
        page_id=first_non_empty(
            rows,
            "Page ID",
        ),
        question_id=first_non_empty(
            rows,
            "Question ID",
        ),
        question_number=(
            first_non_empty(
                rows,
                "Question Number",
            )
        ),
        question_text=question_text,
        question_visible=parse_bool(
            first_non_empty(
                rows,
                "Question Visible",
            )
        ),
        question_type=question_type,
        tag=tag,
        matrix_row=first_non_empty(
            rows,
            "Matrix Row",
        ),
        matrix_column=first_non_empty(
            rows,
            "Matrix Column",
        ),
        do_not_read_options=bool(
            DO_NOT_READ_PATTERN.search(
                question_text
            )
        ),
        dynamic_dependencies=(
            dependencies
        ),
        choice_catalog_status=(
            catalog_status
        ),
        resolution_ready=(
            resolution_ready
        ),
        choices=choices,
    )


def parse_survey_definition_with_info(
    path: Path,
) -> tuple[
    list[SurveyQuestionDefinition],
    SurveyDefinitionLoadInfo,
]:
    rows, load_info = load_rows(
        path
    )

    grouped: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for row in rows:
        tag = clean(
            row.get(
                "tag"
            )
        )

        if tag is None:
            continue

        grouped.setdefault(
            tag,
            [],
        ).append(
            row
        )

    questions = [
        build_question(
            tag=tag,
            rows=question_rows,
        )
        for tag, question_rows
        in grouped.items()
    ]

    return (
        questions,
        load_info,
    )


def parse_survey_definition(
    path: Path,
) -> list[
    SurveyQuestionDefinition
]:
    questions, _ = (
        parse_survey_definition_with_info(
            path
        )
    )

    return questions


def question_map(
    questions: list[
        SurveyQuestionDefinition
    ],
) -> dict[
    str,
    SurveyQuestionDefinition
]:
    return {
        question.tag: question
        for question in questions
    }