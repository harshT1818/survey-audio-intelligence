import numpy as np

from src.full_sample.interview_turns import (
    UNATTRIBUTED,
    build_interview_turns,
    detect_undetected_speech,
    question_turn_rows,
)

RATE = 16000


def signal(seconds, loud=()):
    """Low noise with loud sine stretches at the given (start, end) seconds."""
    rng = np.random.default_rng(0)
    samples = rng.normal(0, 10, int(seconds * RATE))
    t = np.arange(len(samples)) / RATE
    for start, end in loud:
        mask = (t >= start) & (t < end)
        samples[mask] += 2000 * np.sin(2 * np.pi * 220 * t[mask])
    return samples.astype(np.int16)


def segment(index, speaker, start, end):
    return {"segment_index": index, "speaker_id": speaker, "start_sec": start, "end_sec": end}


ROLES = {"S0": {"role": "agent", "confidence": "STRONG"}, "S1": {"role": "respondent", "confidence": "STRONG"}}


def test_loud_speech_without_a_speaker_is_found():
    audio = signal(10, loud=[(1, 3), (5, 6.5)])
    regions = detect_undetected_speech(audio, RATE, covered=[(1, 3)])

    assert len(regions) == 1
    start, end = regions[0]
    assert abs(start - 5) < 0.1 and abs(end - 6.5) < 0.1
    assert all(isinstance(value, float) for value in regions[0])


def test_short_bursts_and_quiet_noise_are_ignored():
    audio = signal(10, loud=[(1, 3), (5, 5.2)])
    assert detect_undetected_speech(audio, RATE, covered=[(1, 3)]) == []


def test_turns_are_built_once_for_the_interview_and_named_by_speaker():
    turns = build_interview_turns(
        [segment(1, "S0", 1.0, 3.0), segment(2, "S0", 3.3, 5.0), segment(3, "S1", 5.5, 7.0)],
        ROLES,
        undetected=[(8.0, 9.0)],
    )

    assert [t["speaker_id"] for t in turns] == ["S0", "S1", UNATTRIBUTED]
    assert turns[0]["source_segment_indices"] == [1, 2]
    assert turns[0]["clip_name"] == "turn_0001_S0.wav"
    assert turns[2]["role"] == "unknown"
    assert turns[2]["undetected_by_diarization"] is True


def test_a_boundary_turn_is_shared_not_duplicated():
    turns = build_interview_turns([segment(1, "S0", 36.6, 38.0), segment(2, "S1", 39.0, 40.0)], ROLES)
    gender = {"evidence_start_sec": 34.0, "evidence_end_sec": 37.7,
              "question_start_sec": 35.5, "question_end_sec": 36.2}
    phone = {"evidence_start_sec": 34.8, "evidence_end_sec": 51.6,
             "question_start_sec": 36.3, "question_end_sec": 50.1}

    gender_rows = question_turn_rows(gender, turns)
    phone_rows = question_turn_rows(phone, turns)

    assert gender_rows[0]["clip_name"] == phone_rows[0]["clip_name"]
    assert gender_rows[0]["end_sec"] == 37.7 and gender_rows[0]["turn_end_sec"] == 38.0
    assert gender_rows[0]["regions"] == ["context_after"]
    assert phone_rows[0]["regions"] == ["core"]
    assert [r["turn_index"] for r in phone_rows] == [1, 2]
