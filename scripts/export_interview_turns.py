"""Export every speaker turn of an interview once, for ASR.

Writes, under data/private/r2/<response_id>/:
  interview_turn_audio/turn_NNNN_<speaker>.wav   one clip per whole turn
  interview_turns.json                           every turn, inside or outside question windows
  prompting_turn_manifest_clean.json             per-question rows referencing those clips

Replaces the per-question clips of export_real_prompting_turns.py, which cut
turns at window edges and transcribed boundary turns once per question.
An existing manifest is moved to per_question_backup/ first.
"""

import argparse
import json
import shutil
import wave
from pathlib import Path

import numpy as np

from scripts.export_real_prompting_turns import export_clip
from src.full_sample.dialogue_segments import normalize_diarization_segments
from src.full_sample.interview_turns import (
    build_interview_turns,
    detect_undetected_speech,
    question_turn_rows,
)

AUDIO_DIR = "interview_turn_audio"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--response-id", required=True)
    parser.add_argument("--max-gap-sec", type=float, default=0.60)
    parser.add_argument("--minimum-turn-sec", type=float, default=0.35)
    parser.add_argument("--padding-sec", type=float, default=0.20)
    parser.add_argument("--no-undetected-speech", action="store_true",
                        help="Skip recovering loud stretches the diarizer did not attribute.")
    args = parser.parse_args()

    sample_dir = Path("data/private/r2") / args.response_id
    roles = load_json(sample_dir / "speaker_roles.json")
    if roles.get("status") not in {"RESOLVED", "AGENT_ONLY"}:
        raise ValueError("Speaker roles are not resolved.")
    questions = load_json(sample_dir / "question_dialogue_segments.json")
    segments = normalize_diarization_segments(load_json(sample_dir / "interview_16k_mono_diarization.json"))
    audio_path = sample_dir / "interview_16k_mono.wav"

    undetected = []
    if not args.no_undetected_speech:
        with wave.open(str(audio_path)) as handle:
            rate = handle.getframerate()
            samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype=np.int16)
        undetected = detect_undetected_speech(samples, rate, [(s["start_sec"], s["end_sec"]) for s in segments])

    turns = build_interview_turns(
        segments, roles["roles"], undetected,
        max_gap_sec=args.max_gap_sec, minimum_turn_sec=args.minimum_turn_sec, padding_sec=args.padding_sec,
    )

    output_dir = sample_dir / AUDIO_DIR
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    for turn in turns:
        turn["audio_file"] = None
        if turn["clip_name"]:
            path = output_dir / turn["clip_name"]
            export_clip(audio_path, path, float(turn["export_start_sec"]), float(turn["export_end_sec"]))
            turn["audio_file"] = str(path)

    # Per-question files from the old export are kept once, untouched; a
    # rerun of this script just replaces its own manifest.
    manifest_path = sample_dir / "prompting_turn_manifest_clean.json"
    if manifest_path.exists():
        old_style = not any("interview_turn_index" in row for row in load_json(manifest_path))
        if old_style:
            backup = sample_dir / "per_question_backup"
            if backup.exists():
                raise FileExistsError(f"{backup} already exists; move it before re-exporting.")
            backup.mkdir()
            for name in ("prompting_turn_manifest_clean.json", "prompting_turn_asr_results_clean.json"):
                if (sample_dir / name).exists():
                    shutil.move(str(sample_dir / name), str(backup / name))

    manifest = []
    for question in questions:
        for row in question_turn_rows(question, turns):
            manifest.append({
                "response_id": args.response_id,
                "tag": question["tag"],
                "question_index": question["question_index"],
                "question_text": question.get("question_text"),
                "stored_response": question.get("stored_response"),
                **row,
                "padded_start_sec": row["export_start_sec"],
                "padded_end_sec": row["export_end_sec"],
            })

    (sample_dir / "interview_turns.json").write_text(json.dumps(turns, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    exported = [t for t in turns if t["clip_name"]]
    in_windows = {row["clip_name"] for row in manifest if row["clip_name"]}
    print(f"Turns:               {len(turns)} ({sum(t['undetected_by_diarization'] for t in turns)} unattributed)")
    print(f"Clips for ASR:       {len(exported)} ({sum(float(t['export_end_sec']) - float(t['export_start_sec']) for t in exported) / 60:.1f} min)")
    print(f"  inside questions:  {len(in_windows)}")
    print(f"  between questions: {len(exported) - len(in_windows)}")
    print(f"Question rows:       {len(manifest)} across {len({r['tag'] for r in manifest})} questions")
    print(f"Saved: {sample_dir / 'interview_turns.json'}")
    print(f"Saved: {manifest_path}")


if __name__ == "__main__":
    main()
