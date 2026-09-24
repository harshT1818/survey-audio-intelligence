import re

from src.resolver.models import CanonicalOption


def parse_surveyxpress_option(
    raw_label: str,
    value: str | None = None,
) -> CanonicalOption:
    raw_label = raw_label.strip()

    labels: list[str] = [raw_label]
    aliases: list[str] = []

    # Remove numeric prefixes such as:
    # "364. बदलापुर [Badlapur]"
    without_number = re.sub(
        r"^\s*\d+\s*[.)-]?\s*",
        "",
        raw_label,
    ).strip()

    if without_number and without_number != raw_label:
        labels.append(without_number)

    # Extract [English/Hindi text]
    square_matches = re.findall(
        r"\[([^\]]+)\]",
        raw_label,
    )

    for match in square_matches:
        cleaned = match.strip()

        if cleaned and cleaned not in labels:
            labels.append(cleaned)

    # Extract <candidate/name text>
    angle_matches = re.findall(
        r"<([^>]+)>",
        raw_label,
    )

    for match in angle_matches:
        cleaned = match.strip()

        if cleaned and cleaned not in labels:
            labels.append(cleaned)

    # Extract *CODE* values such as *BSP*, *ASPKR*
    code_matches = re.findall(
        r"\*([^*]+)\*",
        raw_label,
    )

    for match in code_matches:
        cleaned = match.strip()

        if cleaned and cleaned not in aliases:
            aliases.append(cleaned)

    # Text before first bracket often contains the Hindi label.
    hindi_part = re.split(
        r"[\[<{*]",
        without_number,
        maxsplit=1,
    )[0].strip()

    if hindi_part and hindi_part not in labels:
        labels.append(hindi_part)

    canonical_value = value

    if canonical_value is None:
        if square_matches:
            canonical_value = square_matches[-1].strip()
        else:
            canonical_value = without_number

    return CanonicalOption(
        value=canonical_value,
        labels=list(dict.fromkeys(labels)),
        aliases=list(dict.fromkeys(aliases)),
    )