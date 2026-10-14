import argparse
import csv
import json
from pathlib import Path
from typing import Any


AUDIT_COLUMNS = [
    "audit_project_code",
    "response_id",
    "audit_answer_disposition",
    "audit_date",
    "audit_end_time",
    "audit_question_disposition",
    "audit_response",
    "audit_start_time",
    "audit_status",
    "audit_user_id",
    "audit_user_id_text",
    "date_of_insertion",
    "survey_id",
]


def decode_json_layers(
    value: Any,
    max_layers: int = 5,
) -> Any:
    """
    Audit CRM fields can contain JSON encoded inside
    strings, sometimes more than once.

    Keep decoding until the value is no longer a string
    containing valid JSON.
    """
    current = value

    for _ in range(max_layers):
        if not isinstance(current, str):
            break

        stripped = current.strip()

        if not stripped:
            break

        try:
            current = json.loads(stripped)
        except json.JSONDecodeError:
            break

    return current


def load_audit_row(
    path: Path,
) -> dict[str, str]:
    """
    Load one raw audit_crm_responses CSV row.

    Expected column order is the Cassandra table order
    supplied for this benchmark.
    """
    csv.field_size_limit(
        100_000_000
    )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.reader(file)
        rows = list(reader)

    if len(rows) != 1:
        raise ValueError(
            "Expected exactly one audit row in "
            f"{path}, found {len(rows)}."
        )

    row = rows[0]

    if len(row) != len(AUDIT_COLUMNS):
        raise ValueError(
            "Unexpected audit row schema. "
            f"Expected {len(AUDIT_COLUMNS)} columns, "
            f"found {len(row)}."
        )

    return dict(
        zip(
            AUDIT_COLUMNS,
            row,
        )
    )


def normalize_human_audit(
    raw_value: str,
) -> dict[str, Any]:
    payload = decode_json_layers(
        raw_value
    )

    if not isinstance(payload, dict):
        raise ValueError(
            "audit_answer_disposition did not "
            "decode to a JSON object."
        )

    normalized = {}

    for tag, value in payload.items():
        normalized[tag] = (
            decode_json_layers(value)
        )

    return normalized


def normalize_policy(
    raw_value: str,
) -> list[dict[str, Any]]:
    payload = decode_json_layers(
        raw_value
    )

    if not isinstance(payload, list):
        raise ValueError(
            "audit_question_disposition did not "
            "decode to a JSON list."
        )

    normalized = []

    for raw_item in payload:
        if not isinstance(
            raw_item,
            dict,
        ):
            continue

        item = dict(raw_item)

        disposition = item.get(
            "desposition"
        )

        if disposition is not None:
            item["desposition"] = (
                decode_json_layers(
                    disposition
                )
            )

        normalized.append(item)

    return normalized


def normalize_survey(
    raw_value: str,
) -> dict[str, Any]:
    payload = decode_json_layers(
        raw_value
    )

    if not isinstance(payload, dict):
        raise ValueError(
            "audit_response did not decode "
            "to a JSON object."
        )

    return payload


def build_question_windows(
    policy: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    windows = []

    for item in policy:
        data = item.get("data")

        if not isinstance(
            data,
            dict,
        ):
            continue

        time_logs = data.get(
            "time_logs"
        )

        if not isinstance(
            time_logs,
            list,
        ):
            continue

        valid_logs = []

        for log in time_logs:
            if not isinstance(
                log,
                dict,
            ):
                continue

            start = log.get(
                "start_time"
            )

            end = log.get(
                "end_time"
            )

            if (
                not isinstance(
                    start,
                    (int, float),
                )
                or not isinstance(
                    end,
                    (int, float),
                )
            ):
                continue

            if (
                start < 0
                or end <= start
            ):
                continue

            valid_logs.append(
                {
                    "start_time": start,
                    "end_time": end,
                }
            )

        if not valid_logs:
            continue

        start_ms = min(
            log["start_time"]
            for log in valid_logs
        )

        end_ms = max(
            log["end_time"]
            for log in valid_logs
        )

        active_duration_ms = sum(
            (
                log["end_time"]
                - log["start_time"]
            )
            for log in valid_logs
        )

        windows.append(
            {
                "tag": item.get(
                    "tag"
                ),
                "order": item.get(
                    "order"
                ),
                "question_tag_id": (
                    item.get(
                        "question_tag_id"
                    )
                ),
                "question_text": (
                    data.get(
                        "question_text"
                    )
                ),
                "question_type": (
                    data.get(
                        "question_type"
                    )
                ),
                "raw_response": (
                    data.get(
                        "raw_response"
                    )
                ),
                "english_value": (
                    data.get(
                        "englishVal"
                    )
                ),
                "hindi_value": (
                    data.get(
                        "hindiVal"
                    )
                ),
                "regional_value": (
                    data.get(
                        "regionalVal"
                    )
                ),
                "others": data.get(
                    "others",
                    {},
                ),
                "time_logs": (
                    valid_logs
                ),
                "start_ms": start_ms,
                "end_ms": end_ms,
                "start_sec": round(
                    start_ms / 1000,
                    3,
                ),
                "end_sec": round(
                    end_ms / 1000,
                    3,
                ),
                "window_duration_ms": (
                    end_ms
                    - start_ms
                ),
                "active_duration_ms": (
                    active_duration_ms
                ),
            }
        )

    windows.sort(
        key=lambda item: (
            item["start_ms"],
            item["order"]
            if item.get("order")
            is not None
            else 999999,
        )
    )

    return windows


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--response-id",
        required=True,
    )

    args = parser.parse_args()

    sample_dir = (
        Path("data/private/r2")
        / args.response_id
    )

    source_path = (
        sample_dir
        / "audit_row.csv"
    )

    if not source_path.exists():
        raise FileNotFoundError(
            "\nMissing raw audit export:\n"
            f"{source_path}\n\n"
            "Save the single audit_crm_responses "
            "database row as audit_row.csv first."
        )

    row = load_audit_row(
        source_path
    )

    if (
        row["response_id"]
        != args.response_id
    ):
        raise ValueError(
            "Response ID inside audit_row.csv "
            "does not match --response-id.\n"
            f"Expected: {args.response_id}\n"
            f"Found:    {row['response_id']}"
        )

    human_audit = (
        normalize_human_audit(
            row[
                "audit_answer_disposition"
            ]
        )
    )

    policy = normalize_policy(
        row[
            "audit_question_disposition"
        ]
    )

    survey = normalize_survey(
        row[
            "audit_response"
        ]
    )

    windows = (
        build_question_windows(
            policy
        )
    )

    metadata = {
        "audit_project_code": row[
            "audit_project_code"
        ],
        "response_id": row[
            "response_id"
        ],
        "audit_date": row[
            "audit_date"
        ],
        "audit_start_time": row[
            "audit_start_time"
        ],
        "audit_end_time": row[
            "audit_end_time"
        ],
        "audit_status": row[
            "audit_status"
        ],
        "survey_id": (
            row["survey_id"]
            or None
        ),
    }

    write_json(
        sample_dir
        / "metadata.json",
        metadata,
    )

    write_json(
        sample_dir
        / "human_audit.json",
        human_audit,
    )

    write_json(
        sample_dir
        / "audit_policy_snapshot.json",
        policy,
    )

    write_json(
        sample_dir
        / "survey.json",
        survey,
    )

    write_json(
        sample_dir
        / "question_windows.json",
        windows,
    )

    audited_tags = [
        key
        for key in human_audit
        if key != "remarks"
    ]

    latest_end_ms = max(
        (
            window["end_ms"]
            for window in windows
        ),
        default=0,
    )

    print()
    print(
        "=== REAL SAMPLE PREPARED ==="
    )
    print()

    print(
        f"Response ID:          "
        f"{args.response_id}"
    )

    print(
        f"Project:              "
        f"{metadata['audit_project_code']}"
    )

    print(
        f"Human audited tags:   "
        f"{len(audited_tags)}"
    )

    print(
        f"Audit policy tags:    "
        f"{len(policy)}"
    )

    print(
        f"Survey response tags: "
        f"{len(survey)}"
    )

    print(
        f"Timed questions:      "
        f"{len(windows)}"
    )

    print(
        f"Latest timed offset:  "
        f"{latest_end_ms / 1000:.3f}s"
    )

    print()
    print("Created:")

    for filename in [
        "metadata.json",
        "human_audit.json",
        "audit_policy_snapshot.json",
        "survey.json",
        "question_windows.json",
    ]:
        print(
            f"  {sample_dir / filename}"
        )


if __name__ == "__main__":
    main()