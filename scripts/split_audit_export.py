import argparse
from pathlib import Path

from src.ingestion.audit_export import (
    PROJECT_CODE_INDEX,
    plan_audit_rows,
    read_audit_export,
    write_audit_row,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Split an audit_crm_responses export into "
            "data/private/r2/<response_id>/audit_row.csv files."
        ),
    )
    parser.add_argument("export", type=Path)
    parser.add_argument("--samples-root", type=Path, default=Path("data/private/r2"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    plan = plan_audit_rows(read_audit_export(args.export))

    for response_id, files in sorted(plan.items()):
        for name, row in files.items():
            path = args.samples_root / response_id / name
            status = write_audit_row(path, row, overwrite=args.overwrite)
            print(f"{status:11} {response_id}/{name:22} {row[PROJECT_CODE_INDEX]}")

    print(f"\nResponses: {len(plan)}")


if __name__ == "__main__":
    main()
