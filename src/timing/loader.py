import csv
from dataclasses import dataclass


@dataclass
class SubmissionTiming:
    submission_id: str
    raw_tag_times_ms: dict[str, int | None]

    @property
    def total_tag_duration_ms(self) -> int:
        return sum(
            value
            for value in self.raw_tag_times_ms.values()
            if value is not None
        )

    @property
    def recorded_tag_count(self) -> int:
        return sum(
            value is not None
            for value in self.raw_tag_times_ms.values()
        )


def _parse_duration(value: str) -> int | None:
    value = value.strip()

    if not value:
        return None

    try:
        duration = int(float(value))
    except ValueError:
        return None

    if duration <= 0:
        return None

    return duration


def _detect_delimiter(file) -> str:
    sample = file.read(8192)
    file.seek(0)

    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=",\t;|",
        )
        return dialect.delimiter
    except csv.Error:
        # Standard CSV fallback
        return ","


def load_submission_timings(
    file_path: str,
) -> dict[str, SubmissionTiming]:

    submissions: dict[str, SubmissionTiming] = {}

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        delimiter = _detect_delimiter(file)

        reader = csv.DictReader(
            file,
            delimiter=delimiter,
        )

        if not reader.fieldnames:
            raise ValueError("Timing CSV has no headers")

        # Clean whitespace from column names.
        reader.fieldnames = [
            field.strip()
            for field in reader.fieldnames
        ]

        if "submission_id" not in reader.fieldnames:
            raise ValueError(
                "Timing CSV must contain submission_id. "
                f"Detected delimiter={repr(delimiter)}. "
                f"First columns={reader.fieldnames[:5]}"
            )

        for row in reader:
            submission_id = (
                row.get("submission_id") or ""
            ).strip()

            if not submission_id:
                continue

            timings: dict[str, int | None] = {}

            for tag, raw_value in row.items():
                if tag is None:
                    continue

                tag = tag.strip()

                if tag == "submission_id":
                    continue

                timings[tag] = _parse_duration(
                    raw_value or ""
                )

            submissions[submission_id] = SubmissionTiming(
                submission_id=submission_id,
                raw_tag_times_ms=timings,
            )

    return submissions