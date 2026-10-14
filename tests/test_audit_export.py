import pytest

from src.ingestion.audit_export import (
    PRIMARY_FILE,
    REGULAR_FILE,
    plan_audit_rows,
    read_audit_export,
    write_audit_row,
)

PROJECT = "TEST-PROJECT"
SUPER = "TEST-PROJECT{Super-Audit-123}"


def row(project_code, response_id, answer="{}"):
    return [project_code, response_id, answer, *[f"c{i}" for i in range(10)]]


def test_super_audit_is_primary_and_regular_is_kept():
    plan = plan_audit_rows([
        row(PROJECT, "r1", "regular"),
        row(SUPER, "r1", "super"),
        row(PROJECT, "r2"),
    ])

    assert plan["r1"][PRIMARY_FILE][2] == "super"
    assert plan["r1"][REGULAR_FILE][2] == "regular"
    assert set(plan["r2"]) == {PRIMARY_FILE}


def test_super_audit_only_becomes_primary():
    plan = plan_audit_rows([row(SUPER, "r1")])

    assert set(plan["r1"]) == {PRIMARY_FILE}
    assert plan["r1"][PRIMARY_FILE][0] == SUPER


def test_duplicate_rows_of_one_kind_are_refused():
    with pytest.raises(ValueError, match="2 super audit rows"):
        plan_audit_rows([row(SUPER, "r1"), row("TEST-PROJECT{Super-Audit-9}", "r1")])


def test_export_with_wrong_column_count_is_refused(tmp_path):
    path = tmp_path / "export.csv"
    path.write_text("project,response\n", encoding="utf-8")

    with pytest.raises(ValueError, match="expected 13 columns"):
        read_audit_export(path)


def test_written_row_round_trips_and_is_not_silently_replaced(tmp_path):
    path = tmp_path / "r1" / PRIMARY_FILE
    original = row(PROJECT, "r1", '"{\\"a\\":\\"हाँ, ठीक\\"}"')

    assert write_audit_row(path, original) == "CREATED"
    assert read_audit_export(path) == [original]
    assert write_audit_row(path, original) == "UNCHANGED"

    with pytest.raises(FileExistsError):
        write_audit_row(path, row(PROJECT, "r1", "changed"))

    assert write_audit_row(path, row(PROJECT, "r1", "changed"), overwrite=True) == "OVERWRITTEN"
