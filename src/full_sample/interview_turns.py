"""Speaker turns for a whole interview, each transcribed once.

Per-question export cut a diarization segment at every window edge, so a
turn near a boundary was clipped mid-word and sent to ASR once per
question that included it (22% of clips, 12% of ASR audio in six
interviews), and speech between audited questions (name, caste) was never
transcribed. Here turns are built once for the interview, exported once as
whole utterances, and each question references the turns that overlap its
window. Speech the diarizer did not attribute to anyone, such as a quiet or
distant respondent, is recovered by loudness as "unattributed" turns: it is
transcribed and shown, but never used for automatic decisions.
"""

from typing import Any

import numpy as np

from src.full_sample.speaker_safe_export import speaker_safe_export_bounds
from src.full_sample.speaker_turns import (
    add_role_to_turns,
    mark_turn_exportability,
    merge_same_speaker_segments,
)

UNATTRIBUTED = "unattributed"


def detect_undetected_speech(
    samples: np.ndarray,
    sample_rate: int,
    covered: list[tuple[float, float]],
    frame_sec: float = 0.03,
    min_region_sec: float = 0.5,
    merge_gap_sec: float = 0.3,
    noise_multiplier: float = 4.0,
    speech_fraction: float = 0.1,
) -> list[tuple[float, float]]:
    """Loud stretches that no diarization segment covers.

    A frame counts as sound when its RMS is above both a multiple of the
    recording's noise floor (10th percentile) and a fraction of the typical
    level inside diarized speech, so background hum does not qualify but a
    soft voice does.
    """
    frame = max(1, int(sample_rate * frame_sec))
    count = len(samples) // frame
    if count == 0:
        return []
    frames = samples[: count * frame].astype(np.float64).reshape(count, frame)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))

    is_covered = np.zeros(count, dtype=bool)
    for start, end in covered:
        is_covered[max(0, int(start / frame_sec)): min(count, int(np.ceil(end / frame_sec)))] = True

    noise = float(np.percentile(rms, 10))
    speech_level = float(np.median(rms[is_covered])) if is_covered.any() else float(np.percentile(rms, 90))
    threshold = max(noise_multiplier * noise, speech_fraction * speech_level)
    active = (rms > threshold) & ~is_covered

    regions, start, last = [], None, None
    max_gap = int(round(merge_gap_sec / frame_sec))
    for index in np.flatnonzero(active):
        if start is None:
            start = last = index
        elif index - last <= max_gap and not is_covered[last + 1: index].any():
            last = index
        else:
            regions.append((start, last))
            start = last = index
    if start is not None:
        regions.append((start, last))

    return [
        (round(float(a) * frame_sec, 3), round(float(b + 1) * frame_sec, 3))
        for a, b in regions
        if (b + 1 - a) * frame_sec >= min_region_sec
    ]


def build_interview_turns(
    diarization_segments: list[dict[str, Any]],
    roles: dict[str, Any],
    undetected: list[tuple[float, float]] = (),
    max_gap_sec: float = 0.60,
    minimum_turn_sec: float = 0.35,
    padding_sec: float = 0.20,
) -> list[dict[str, Any]]:
    """Whole-interview turns with roles, export flags and speaker-safe bounds.

    diarization_segments are normalized segments (segment_index, speaker_id,
    start_sec, end_sec). Clip names carry the speaker, not the role, so a
    later role correction does not invalidate transcripts.
    """
    merge_input = [
        {
            "segment_index": s["segment_index"],
            "speaker_id": s["speaker_id"],
            "clipped_start_sec": s["start_sec"],
            "clipped_end_sec": s["end_sec"],
            "region": "interview",
            "touches_core": False,
        }
        for s in diarization_segments
    ]
    turns = merge_same_speaker_segments(merge_input, max_gap_sec=max_gap_sec)
    for start, end in undetected:
        turns.append({
            "speaker_id": UNATTRIBUTED,
            "start_sec": start,
            "end_sec": end,
            "duration_sec": round(end - start, 3),
            "source_segment_indices": [],
            "regions": ["interview"],
            "touches_core": False,
        })
    turns.sort(key=lambda t: (float(t["start_sec"]), float(t["end_sec"])))
    for turn in turns:
        turn["duration_sec"] = round(float(turn["end_sec"]) - float(turn["start_sec"]), 3)

    turns = mark_turn_exportability(add_role_to_turns(turns, roles), minimum_duration_sec=minimum_turn_sec)

    output = []
    for number, turn in enumerate(turns, start=1):
        bounds = speaker_safe_export_bounds(turn=turn, all_turns=turns, padding_sec=padding_sec)
        output.append({
            **turn,
            **bounds,
            "turn_index": number,
            "interview_turn_index": number,
            "undetected_by_diarization": turn["speaker_id"] == UNATTRIBUTED,
            "clip_name": (
                f"turn_{number:04d}_{turn['speaker_id']}.wav" if turn["export_for_asr"] else None
            ),
        })
    return output


def question_turn_rows(
    question: dict[str, Any],
    interview_turns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rows for one question: interview turns overlapping its evidence window.

    Timing is clipped to the window, exactly as per-question export did, so
    anchoring and region logic are unchanged; the audio and transcript are
    the shared whole turn.
    """
    evidence_start = float(question["evidence_start_sec"])
    evidence_end = float(question["evidence_end_sec"])
    core_start = float(question["question_start_sec"])
    core_end = float(question["question_end_sec"])

    rows = []
    for turn in interview_turns:
        start = max(float(turn["start_sec"]), evidence_start)
        end = min(float(turn["end_sec"]), evidence_end)
        if end <= start:
            continue
        if end > core_start and start < core_end:
            region = "core"
        elif end <= core_start:
            region = "context_before"
        else:
            region = "context_after"
        rows.append({
            **turn,
            "turn_index": len(rows) + 1,
            "turn_start_sec": turn["start_sec"],
            "turn_end_sec": turn["end_sec"],
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "duration_sec": round(end - start, 3),
            "regions": [region],
            "touches_core": region == "core",
        })
    return rows
