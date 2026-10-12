"""Compare diarization outputs against listened-to checkpoints.

A checkpoint is a time range a person listened to, with what they heard:

- "agent": mostly interviewer speech
- "respondent": mostly respondent speech
- "mixed": both speak inside the range (e.g. question then answer)

Checkpoints marked "unsure" are reported but not scored. This is a smoke
test on a handful of moments, not a diarization error rate.
"""

from collections import defaultdict
from typing import Any

EXPECTATIONS = {"agent", "respondent", "mixed"}

# Minimum seconds of a speaker inside a "mixed" range for it to count.
MIXED_MIN_SPEECH_SEC = 0.3


def _overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def speaker_seconds(
    segments: list[dict[str, Any]],
    start_sec: float,
    end_sec: float,
) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for segment in segments:
        seconds = _overlap(
            float(segment["start_sec"]), float(segment["end_sec"]),
            start_sec, end_sec,
        )
        if seconds > 0:
            totals[str(segment["speaker_id"])] += seconds
    return {speaker: round(seconds, 3) for speaker, seconds in totals.items()}


def speaker_totals(segments: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for segment in segments:
        totals[str(segment["speaker_id"])] += (
            float(segment["end_sec"]) - float(segment["start_sec"])
        )
    return {speaker: round(seconds, 1) for speaker, seconds in sorted(totals.items())}


def agent_speaker(
    segments: list[dict[str, Any]],
    checkpoints: list[dict[str, Any]],
) -> str | None:
    """Speaker with the most speech inside agent checkpoints."""
    totals: dict[str, float] = defaultdict(float)
    for checkpoint in checkpoints:
        if checkpoint["expected"] != "agent" or checkpoint.get("unsure"):
            continue
        for speaker, seconds in speaker_seconds(
            segments, checkpoint["start_sec"], checkpoint["end_sec"],
        ).items():
            totals[speaker] += seconds
    if not totals:
        return None
    return max(totals, key=totals.get)


def score_checkpoint(
    checkpoint: dict[str, Any],
    segments: list[dict[str, Any]],
    agent: str | None,
) -> dict[str, Any]:
    expected = checkpoint["expected"]
    if expected not in EXPECTATIONS:
        raise ValueError(f"Unknown expectation: {expected}")

    seconds = speaker_seconds(segments, checkpoint["start_sec"], checkpoint["end_sec"])
    agent_sec = seconds.get(agent, 0.0) if agent else 0.0
    other_sec = round(sum(seconds.values()) - agent_sec, 3)
    covered = agent_sec + other_sec

    if agent is None or covered == 0:
        verdict = "NO_SPEECH" if covered == 0 else "NO_AGENT_REFERENCE"
    elif expected == "agent":
        verdict = "PASS" if agent_sec > other_sec else "FAIL"
    elif expected == "respondent":
        verdict = "PASS" if other_sec > agent_sec else "FAIL"
    else:
        verdict = (
            "PASS"
            if agent_sec >= MIXED_MIN_SPEECH_SEC and other_sec >= MIXED_MIN_SPEECH_SEC
            else "FAIL"
        )

    return {
        "label": checkpoint.get("label"),
        "expected": expected,
        "unsure": bool(checkpoint.get("unsure")),
        "speaker_seconds": seconds,
        "agent_sec": round(agent_sec, 3),
        "other_sec": other_sec,
        "verdict": verdict,
    }


def compare_diarization(
    diarization: dict[str, Any],
    checkpoints: list[dict[str, Any]],
) -> dict[str, Any]:
    segments = diarization["segments"]
    agent = agent_speaker(segments, checkpoints)
    results = [score_checkpoint(c, segments, agent) for c in checkpoints]
    scored = [r for r in results if not r["unsure"]]
    return {
        "model_name": diarization.get("model_name"),
        "speaker_totals_sec": speaker_totals(segments),
        "agent_speaker": agent,
        "passed": sum(r["verdict"] == "PASS" for r in scored),
        "scored": len(scored),
        "checkpoints": results,
    }
