"""Split an audit_crm_responses export into per-response audit rows.

The export has no header; columns follow the table's SELECT * order,
the same layout scripts/prepare_real_sample.py reads from audit_row.csv.
"""

import csv
from pathlib import Path

AUDIT_COLUMN_COUNT = 13
PROJECT_CODE_INDEX = 0
RESPONSE_ID_INDEX = 1

SUPER_AUDIT_MARKER = "{Super-Audit-"

PRIMARY_FILE = "audit_row.csv"
REGULAR_FILE = "audit_row_regular.csv"


def is_super_audit(project_code: str) -> bool:
    return SUPER_AUDIT_MARKER in project_code


def read_audit_export(path: Path) -> list[list[str]]:
    csv.field_size_limit(100_000_000)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = [row for row in csv.reader(file) if row]

    for number, row in enumerate(rows, start=1):
        if len(row) != AUDIT_COLUMN_COUNT:
            raise ValueError(
                f"Row {number}: expected {AUDIT_COLUMN_COUNT} columns, "
                f"found {len(row)}. Export without a header, in SELECT * order."
            )

    return rows


def plan_audit_rows(
    rows: list[list[str]],
) -> dict[str, dict[str, list[str]]]:
    """Choose which row each response keeps, keyed by response ID.

    The super-audit row is the primary audit when present; the regular
    audit is kept alongside it. More than one row of the same kind for
    a response is ambiguous and refused.
    """
    grouped: dict[str, dict[str, list[list[str]]]] = {}

    for row in rows:
        kind = "super" if is_super_audit(row[PROJECT_CODE_INDEX]) else "regular"
        grouped.setdefault(row[RESPONSE_ID_INDEX], {}).setdefault(kind, []).append(row)

    plan = {}

    for response_id, kinds in grouped.items():
        for kind, kind_rows in kinds.items():
            if len(kind_rows) > 1:
                raise ValueError(
                    f"{response_id}: {len(kind_rows)} {kind} audit rows; "
                    "keep one per response in the export."
                )

        files = {}
        if "super" in kinds:
            files[PRIMARY_FILE] = kinds["super"][0]
            if "regular" in kinds:
                files[REGULAR_FILE] = kinds["regular"][0]
        else:
            files[PRIMARY_FILE] = kinds["regular"][0]

        plan[response_id] = files

    return plan


def read_single_row(path: Path) -> list[str]:
    csv.field_size_limit(100_000_000)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = [row for row in csv.reader(file) if row]

    if len(rows) != 1:
        raise ValueError(f"Expected one row in {path}, found {len(rows)}.")

    return rows[0]


def write_audit_row(
    path: Path,
    row: list[str],
    overwrite: bool = False,
) -> str:
    """Write one row; return CREATED, UNCHANGED or OVERWRITTEN.

    An existing file with different content is refused unless
    overwrite is set, so earlier samples are never silently replaced.
    """
    if path.exists():
        if read_single_row(path) == row:
            return "UNCHANGED"
        if not overwrite:
            raise FileExistsError(
                f"{path} already holds a different audit row. "
                "Pass --overwrite to replace it."
            )
        status = "OVERWRITTEN"
    else:
        status = "CREATED"

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        csv.writer(file).writerow(row)

    return status
