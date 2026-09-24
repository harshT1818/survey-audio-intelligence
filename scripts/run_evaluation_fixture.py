import argparse

from src.evaluation.runner import (
    load_evaluation_fixture,
    run_evaluation_fixture,
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "fixture_path",
        help=(
            "Path to evaluation fixture JSON."
        ),
    )

    args = parser.parse_args()

    fixture = load_evaluation_fixture(
        args.fixture_path
    )

    summary = run_evaluation_fixture(
        fixture
    )

    print()
    print(
        f"=== {summary.fixture_name} ==="
    )
    print()

    for result in summary.results:
        status = (
            "PASS"
            if result.passed
            else "FAIL"
        )

        print(
            f"[{status}] {result.case_id}"
        )

        if result.failures:
            for failure in result.failures:
                print(
                    f"    - {failure}"
                )

    print()
    print(
        f"Passed: "
        f"{summary.passed_cases}/"
        f"{summary.total_cases}"
    )

    print(
        f"Failed: "
        f"{summary.failed_cases}/"
        f"{summary.total_cases}"
    )

    if summary.failed_cases:
        raise SystemExit(1)


if __name__ == "__main__":
    main()