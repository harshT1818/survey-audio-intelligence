import argparse
import json
from pathlib import Path

from src.full_sample.dialogue_merge import (
    asr_coverage,
    coverage_blockers,
    merge_dialogues_by_tag,
)
from src.full_sample.prompting_dialogue import build_prompting_dialogue


def load_list(path: Path) -> list:
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"{path.name} must be a JSON list.")
    return data


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build role dialogue for a turn ASR batch and merge it by tag into "
            "an existing dialogue file without overwriting existing tags."
        ),
    )
    parser.add_argument("--sample-dir", type=Path, required=True)
    parser.add_argument("--manifest", default="full_sample_pending_turn_manifest.json")
    parser.add_argument("--asr-results", default="full_sample_pending_turn_asr_results.json")
    parser.add_argument("--dialogue", default="prompting_dialogue_clean.json")
    parser.add_argument(
        "--allow-incomplete", action="store_true",
        help="Merge despite missing/unexpected/duplicate ASR rows.",
    )
    args = parser.parse_args()

    manifest = load_list(args.sample_dir / args.manifest)
    asr_results = load_list(args.sample_dir / args.asr_results)
    dialogue_path = args.sample_dir / args.dialogue
    existing = load_list(dialogue_path)

    coverage = asr_coverage(manifest, asr_results)
    blockers = coverage_blockers(coverage)
    print(f"Expected clips: {coverage['expected']}")
    print(f"ASR rows:       {coverage['received']}")
    print(f"Empty:          {len(coverage['empty'])}")
    for key in ("missing", "unexpected", "duplicates"):
        for name in coverage[key]:
            print(f"  {key.upper():10} {name}")
    if blockers and not args.allow_incomplete:
        raise SystemExit(f"Refusing to merge ({', '.join(blockers)}); use --allow-incomplete.")

    additional = build_prompting_dialogue(manifest=manifest, asr_results=asr_results)
    merged = merge_dialogues_by_tag(existing, additional)

    backup_path = dialogue_path.with_name(f"{dialogue_path.stem}.before_merge.json")
    if backup_path.exists():
        raise SystemExit(f"Backup already exists, not overwriting: {backup_path}")
    backup_path.write_text(dialogue_path.read_text(encoding="utf-8-sig"), encoding="utf-8")

    dialogue_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"Existing tags:  {len(existing)}")
    print(f"Added tags:     {len(additional)}")
    print(f"Merged tags:    {len(merged)}")
    for dialogue in additional:
        print(f"  {dialogue['tag']:32} {dialogue.get('evidence_status')}")
    print(f"Backup: {backup_path}")
    print(f"Saved:  {dialogue_path}")


if __name__ == "__main__":
    main()
