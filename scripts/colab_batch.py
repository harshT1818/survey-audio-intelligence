"""Pack several samples for one Colab run, then unpack the results.

  pack-audio         -> sortformer_batch.zip (<response_id>.wav each)
  unpack-diarization <zip of <response_id>_diarization_sortformer.json>
  pack-turns         -> turns_batch.zip + turns_batch_manifest.json
  unpack-asr         <turns_batch_asr_results.json>

Results are written into data/private/r2/<response_id>/ and never
replace a different existing file unless --overwrite is passed.
"""

import argparse
import json
import zipfile
from pathlib import Path

from src.full_sample.colab_batch import (
    combine_turn_manifests,
    diarization_response_id,
    prefixed_clip_name,
    split_asr_results,
)
from src.full_sample.dialogue_merge import asr_coverage, coverage_blockers
from src.full_sample.prompting_dialogue import basename

SAMPLES_ROOT = Path("data/private/r2")
BATCH_DIR = Path("data/private/colab")

AUDIO_NAME = "interview_16k_mono.wav"
DIARIZATION_NAME = "interview_16k_mono_diarization.json"
TURN_MANIFEST_NAME = "prompting_turn_manifest_clean.json"
TURN_AUDIO_DIR = "prompting_turn_audio_clean"
TURN_ASR_NAME = "prompting_turn_asr_results_clean.json"
INTERVIEW_TURNS_NAME = "interview_turns.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json_safely(path: Path, payload, overwrite: bool) -> str:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if path.exists():
        if load_json(path) == payload:
            return "UNCHANGED"
        if not overwrite:
            raise FileExistsError(f"{path} exists with different content; pass --overwrite.")
    path.write_text(text, encoding="utf-8")
    return "WRITTEN"


def pack_audio(response_ids: list[str], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as archive:
        for response_id in response_ids:
            source = SAMPLES_ROOT / response_id / AUDIO_NAME
            if not source.exists():
                raise FileNotFoundError(source)
            archive.write(source, f"{response_id}.wav")
            print(f"  {response_id}.wav")
    print(f"Saved: {output}  ({output.stat().st_size / 1e6:.1f} MB)")


def unpack_diarization(archive_path: Path, overwrite: bool) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        for name in sorted(archive.namelist()):
            file_name = Path(name).name
            if not file_name.endswith(".json"):
                continue
            response_id = diarization_response_id(file_name)
            payload = json.loads(archive.read(name).decode("utf-8"))
            if payload.get("audio_id") != response_id:
                raise ValueError(f"{file_name}: audio_id is {payload.get('audio_id')!r}")
            sample_dir = SAMPLES_ROOT / response_id
            if not sample_dir.is_dir():
                raise FileNotFoundError(sample_dir)
            status = write_json_safely(sample_dir / DIARIZATION_NAME, payload, overwrite)
            print(f"  {status:9} {response_id}  {len(payload['segments'])} segments  {payload.get('model_name')}")


def sample_turns(response_id: str) -> list[dict]:
    """Turns to transcribe: the whole interview when exported that way."""
    interview = SAMPLES_ROOT / response_id / INTERVIEW_TURNS_NAME
    if interview.exists():
        return load_json(interview)
    return load_json(SAMPLES_ROOT / response_id / TURN_MANIFEST_NAME)


def clip_source(response_id: str, row: dict) -> Path:
    path = Path(str(row.get("audio_file") or ""))
    if path.is_file():
        return path
    return SAMPLES_ROOT / response_id / TURN_AUDIO_DIR / basename(row.get("audio_file"))


def pack_turns(response_ids: list[str], output_dir: Path) -> None:
    manifests = {response_id: sample_turns(response_id) for response_id in response_ids}
    combined = combine_turn_manifests(manifests)

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / "turns_batch.zip"
    clip_count = 0
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        added = set()
        for response_id, rows in manifests.items():
            for row in rows:
                clip_name = basename(row.get("audio_file"))
                if not row.get("export_for_asr") or not clip_name:
                    continue
                arcname = prefixed_clip_name(response_id, clip_name)
                if arcname in added:
                    continue
                archive.write(clip_source(response_id, row), arcname)
                added.add(arcname)
                clip_count += 1
            print(f"  {response_id}  {sum(1 for r in rows if r.get('export_for_asr'))} clips")

    manifest_path = output_dir / "turns_batch_manifest.json"
    manifest_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Clips: {clip_count}")
    print(f"Saved: {archive_path}  ({archive_path.stat().st_size / 1e6:.1f} MB)")
    print(f"Saved: {manifest_path}")


def unpack_asr(results_path: Path, overwrite: bool, allow_incomplete: bool) -> None:
    manifest = load_json(results_path.parent / "turns_batch_manifest.json")
    response_ids = {row["response_id"] for row in manifest}
    split = split_asr_results(load_json(results_path), response_ids)

    for response_id in sorted(response_ids):
        coverage = asr_coverage(sample_turns(response_id), split[response_id])
        blockers = coverage_blockers(coverage)
        print(f"  {response_id}  expected={coverage['expected']} received={coverage['received']} "
              f"empty={len(coverage['empty'])} {'; '.join(blockers) or 'OK'}")
        if blockers and not allow_incomplete:
            raise ValueError(f"{response_id}: incomplete ASR ({'; '.join(blockers)}).")

    for response_id in sorted(response_ids):
        status = write_json_safely(SAMPLES_ROOT / response_id / TURN_ASR_NAME, split[response_id], overwrite)
        print(f"  {status:9} {response_id}/{TURN_ASR_NAME}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("pack-audio")
    p.add_argument("--response-ids", nargs="+", required=True)
    p.add_argument("--output", type=Path, default=BATCH_DIR / "sortformer_batch.zip")

    p = sub.add_parser("unpack-diarization")
    p.add_argument("archive", type=Path)
    p.add_argument("--overwrite", action="store_true")

    p = sub.add_parser("pack-turns")
    p.add_argument("--response-ids", nargs="+", required=True)
    p.add_argument("--output-dir", type=Path, default=BATCH_DIR)

    p = sub.add_parser("unpack-asr")
    p.add_argument("results", type=Path)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--allow-incomplete", action="store_true")

    args = parser.parse_args()

    if args.command == "pack-audio":
        pack_audio(args.response_ids, args.output)
    elif args.command == "unpack-diarization":
        unpack_diarization(args.archive, args.overwrite)
    elif args.command == "pack-turns":
        pack_turns(args.response_ids, args.output_dir)
    else:
        unpack_asr(args.results, args.overwrite, args.allow_incomplete)


if __name__ == "__main__":
    main()
