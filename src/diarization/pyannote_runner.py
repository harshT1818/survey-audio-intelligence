import os
import wave
from pathlib import Path

import numpy as np
import torch
from pyannote.audio import Pipeline

from src.diarization.models import (
    DiarizationResult,
    DiarizationSegment,
)


MODEL_NAME = (
    "pyannote/"
    "speaker-diarization-community-1"
)


def load_pipeline():
    token = os.getenv(
        "HF_TOKEN"
    )

    if not token:
        raise RuntimeError(
            "HF_TOKEN environment variable is not set."
        )

    return Pipeline.from_pretrained(
        MODEL_NAME,
        token=token,
    )


def _load_wav_as_waveform(
    audio_path: Path,
) -> dict:
    with wave.open(
        str(audio_path),
        "rb",
    ) as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()

        if sample_width != 2:
            raise ValueError(
                "Expected 16-bit PCM WAV."
            )

        raw_audio = wav.readframes(
            wav.getnframes()
        )

    samples = np.frombuffer(
        raw_audio,
        dtype=np.int16,
    ).astype(
        np.float32
    )

    samples /= 32768.0

    if channels > 1:
        samples = samples.reshape(
            -1,
            channels,
        )

        samples = samples.mean(
            axis=1
        )

    waveform = torch.from_numpy(
        samples
    ).unsqueeze(0)

    return {
        "waveform": waveform,
        "sample_rate": sample_rate,
    }


def diarize_audio(
    audio_path: str | Path,
    audio_id: str,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
) -> DiarizationResult:

    audio_path = Path(
        audio_path
    )

    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio not found: {audio_path}"
        )

    pipeline = load_pipeline()

    audio = _load_wav_as_waveform(
        audio_path
    )

    kwargs = {}

    if min_speakers is not None:
        kwargs["min_speakers"] = (
            min_speakers
        )

    if max_speakers is not None:
        kwargs["max_speakers"] = (
            max_speakers
        )

    output = pipeline(
        audio,
        **kwargs,
    )

    segments = []

    for segment, speaker in (
        output.speaker_diarization
    ):
        segments.append(
            DiarizationSegment(
                speaker_id=str(
                    speaker
                ),
                start_sec=round(
                    float(
                        segment.start
                    ),
                    3,
                ),
                end_sec=round(
                    float(
                        segment.end
                    ),
                    3,
                ),
            )
        )

    return DiarizationResult(
        audio_id=audio_id,
        model_name=MODEL_NAME,
        segments=segments,
    )