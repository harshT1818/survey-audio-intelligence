import json
import math
import wave
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field


class RefinedClip(BaseModel):
    clip_id: str
    source_segment_id: str

    start_sec: float = Field(
        ge=0,
    )

    end_sec: float = Field(
        gt=0,
    )

    reason: str
    clip_path: str


class RefinementManifest(BaseModel):
    audio_id: str
    source_audio: str

    clips: list[RefinedClip] = Field(
        default_factory=list
    )


def read_pcm16_mono_wav(
    audio_path: str | Path,
) -> tuple[
    np.ndarray,
    int,
]:
    audio_path = Path(
        audio_path
    )

    with wave.open(
        str(audio_path),
        "rb",
    ) as wav_file:
        channels = (
            wav_file.getnchannels()
        )

        sample_width = (
            wav_file.getsampwidth()
        )

        sample_rate = (
            wav_file.getframerate()
        )

        if channels != 1:
            raise ValueError(
                "Expected mono WAV."
            )

        if sample_width != 2:
            raise ValueError(
                "Expected 16-bit PCM WAV."
            )

        raw = wav_file.readframes(
            wav_file.getnframes()
        )

    samples = np.frombuffer(
        raw,
        dtype=np.int16,
    )

    return (
        samples,
        sample_rate,
    )


def _rms(
    values: np.ndarray,
) -> float:
    if len(values) == 0:
        return 0.0

    float_values = values.astype(
        np.float32
    )

    return float(
        np.sqrt(
            np.mean(
                float_values
                * float_values
            )
        )
    )


def calculate_frame_energy(
    samples: np.ndarray,
    sample_rate: int,
    frame_sec: float = 0.02,
    hop_sec: float = 0.01,
) -> list[
    tuple[
        float,
        float,
    ]
]:
    frame_size = max(
        1,
        int(
            frame_sec
            * sample_rate
        ),
    )

    hop_size = max(
        1,
        int(
            hop_sec
            * sample_rate
        ),
    )

    result = []

    for start in range(
        0,
        max(
            1,
            len(samples)
            - frame_size
            + 1,
        ),
        hop_size,
    ):
        end = min(
            len(samples),
            start + frame_size,
        )

        frame = samples[
            start:end
        ]

        if len(frame) == 0:
            continue

        time_sec = (
            start / sample_rate
        )

        result.append(
            (
                time_sec,
                _rms(frame),
            )
        )

    return result


def find_silence_split_points(
    samples: np.ndarray,
    sample_rate: int,
    min_silence_sec: float = 0.18,
    threshold_quantile: float = 0.20,
    frame_sec: float = 0.02,
    hop_sec: float = 0.01,
) -> list[float]:
    energy = calculate_frame_energy(
        samples=samples,
        sample_rate=sample_rate,
        frame_sec=frame_sec,
        hop_sec=hop_sec,
    )

    if not energy:
        return []

    energies = np.array(
        [
            value
            for _, value
            in energy
        ],
        dtype=np.float32,
    )

    threshold = float(
        np.quantile(
            energies,
            threshold_quantile,
        )
    )

    silent_flags = [
        value <= threshold
        for _, value in energy
    ]

    min_frames = max(
        1,
        math.ceil(
            min_silence_sec
            / hop_sec
        ),
    )

    split_points = []

    start_index = None

    for index, is_silent in enumerate(
        silent_flags
    ):
        if (
            is_silent
            and start_index is None
        ):
            start_index = index

        if (
            not is_silent
            and start_index is not None
        ):
            silent_length = (
                index
                - start_index
            )

            if silent_length >= min_frames:
                start_time = energy[
                    start_index
                ][0]

                end_time = energy[
                    index - 1
                ][0]

                split_points.append(
                    (
                        start_time
                        + end_time
                    )
                    / 2
                )

            start_index = None

    if start_index is not None:
        silent_length = (
            len(silent_flags)
            - start_index
        )

        if silent_length >= min_frames:
            start_time = energy[
                start_index
            ][0]

            end_time = energy[
                -1
            ][0]

            split_points.append(
                (
                    start_time
                    + end_time
                )
                / 2
            )

    return split_points


def build_split_intervals(
    segment_start_sec: float,
    segment_end_sec: float,
    split_points_local_sec: list[float],
    min_piece_sec: float = 0.45,
) -> list[
    tuple[
        float,
        float,
    ]
]:
    boundaries = [
        segment_start_sec
    ]

    for split_point in (
        split_points_local_sec
    ):
        absolute_point = (
            segment_start_sec
            + split_point
        )

        if (
            absolute_point
            <= segment_start_sec
            or absolute_point
            >= segment_end_sec
        ):
            continue

        boundaries.append(
            absolute_point
        )

    boundaries.append(
        segment_end_sec
    )

    boundaries = sorted(
        set(boundaries)
    )

    intervals = []

    for index in range(
        len(boundaries) - 1
    ):
        start = boundaries[
            index
        ]

        end = boundaries[
            index + 1
        ]

        duration = (
            end - start
        )

        if duration >= min_piece_sec:
            intervals.append(
                (
                    round(
                        start,
                        3,
                    ),
                    round(
                        end,
                        3,
                    ),
                )
            )

    if not intervals:
        return [
            (
                round(
                    segment_start_sec,
                    3,
                ),
                round(
                    segment_end_sec,
                    3,
                ),
            )
        ]

    return intervals


def padded_interval(
    start_sec: float,
    end_sec: float,
    audio_duration_sec: float,
    padding_sec: float = 0.20,
) -> tuple[
    float,
    float,
]:
    start = max(
        0.0,
        start_sec - padding_sec,
    )

    end = min(
        audio_duration_sec,
        end_sec + padding_sec,
    )

    return (
        round(
            start,
            3,
        ),
        round(
            end,
            3,
        ),
    )


def write_wav_clip(
    samples: np.ndarray,
    sample_rate: int,
    start_sec: float,
    end_sec: float,
    destination: str | Path,
) -> None:
    destination = Path(
        destination
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    start_sample = max(
        0,
        int(
            start_sec
            * sample_rate
        ),
    )

    end_sample = min(
        len(samples),
        int(
            end_sec
            * sample_rate
        ),
    )

    clip_samples = samples[
        start_sample:end_sample
    ]

    with wave.open(
        str(destination),
        "wb",
    ) as wav_file:
        wav_file.setnchannels(
            1
        )

        wav_file.setsampwidth(
            2
        )

        wav_file.setframerate(
            sample_rate
        )

        wav_file.writeframes(
            clip_samples.astype(
                np.int16
            ).tobytes()
        )


def save_refinement_manifest(
    manifest: RefinementManifest,
    file_path: str | Path,
) -> None:
    file_path = Path(
        file_path
    )

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path.write_text(
        json.dumps(
            manifest.model_dump(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )