from collections import Counter
from typing import Any

from src.full_sample.prompting_dialogue import basename


def asr_coverage(
    manifest: list[dict[str, Any]],
    asr_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare ASR result rows with the clips a turn manifest exported."""
    expected = sorted({
        basename(row.get("audio_file"))
        for row in manifest
        if row.get("export_for_asr") and row.get("audio_file")
    })
    names = [basename(row.get("audio_file")) for row in asr_results]
    counts = Counter(name for name in names if name)
    received = set(counts)

    return {
        "expected": len(expected),
        "received": len(asr_results),
        "missing": [name for name in expected if name not in received],
        "unexpected": sorted(received - set(expected)),
        "duplicates": sorted(name for name, count in counts.items() if count > 1),
        "unnamed_rows": sum(1 for name in names if not name),
        "empty": sorted(
            basename(row.get("audio_file"))
            for row in asr_results
            if basename(row.get("audio_file"))
            and not str(row.get("transcript") or "").strip()
        ),
    }


def coverage_blockers(coverage: dict[str, Any]) -> list[str]:
    """Coverage problems that make a merge unsafe without explicit approval.

    Empty transcripts are not blockers: they surface as EMPTY turns.
    """
    blockers = []
    for key in ("missing", "unexpected", "duplicates"):
        if coverage[key]:
            blockers.append(f"{key}: {len(coverage[key])}")
    if coverage["unnamed_rows"]:
        blockers.append(f"unnamed_rows: {coverage['unnamed_rows']}")
    return blockers


def merge_dialogues_by_tag(
    existing: list[dict[str, Any]],
    additional: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Combine question dialogues, refusing any repeated tag.

    Existing evidence is never overwritten; dialogues are returned unchanged,
    ordered by question index where available.
    """
    seen: set[str] = set()
    for source, dialogues in (("existing", existing), ("additional", additional)):
        for dialogue in dialogues:
            tag = dialogue.get("tag")
            if not tag:
                raise ValueError(f"{source} dialogue without a tag")
            if tag in seen:
                raise ValueError(f"Duplicate dialogue tag: {tag}")
            seen.add(tag)

    merged = [*existing, *additional]
    return sorted(
        merged,
        key=lambda item: (
            item.get("question_index") is None,
            item.get("question_index") or 0,
        ),
    )
