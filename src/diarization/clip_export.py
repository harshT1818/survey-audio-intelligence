import json
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from src.diarization.models import (
    DiarizationResult,
    DiarizationSegment,
)


class SpeakerClip(BaseModel):
    clip_id: str

    speaker_id: str

    start_sec: float = Field(
        ge=0,
    )

    end_sec: float = Field(
        gt=0,
    )

    clip_path: str


class SpeakerClipManifest(BaseModel):
    audio_id: str

    source_audio: str

    clips: list[SpeakerClip] = Field(
        default_factory=list
    )


def load_diarization_result(
    file_path: str | Path,
) -> DiarizationResult:
    file_path = Path(file_path)

    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    return DiarizationResult.model_validate(
        payload
    )


def merge_speaker_segments(
    segments: list[DiarizationSegment],
    max_gap_sec: float = 0.5,
    min_duration_sec: float = 0.25,
) -> list[DiarizationSegment]:

    useful_segments = [
        segment
        for segment in segments
        if (
            segment.end_sec
            - segment.start_sec
        ) >= min_duration_sec
    ]

    useful_segments.sort(
        key=lambda segment: (
            segment.start_sec,
            segment.end_sec,
        )
    )

    if not useful_segments:
        return []

    merged: list[DiarizationSegment] = []

    for segment in useful_segments:
        if not merged:
            merged.append(
                segment.model_copy()
            )
            continue

        previous = merged[-1]

        gap = (
            segment.start_sec
            - previous.end_sec
        )

        same_speaker = (
            segment.speaker_id
            == previous.speaker_id
        )

        if (
            same_speaker
            and gap >= 0
            and gap <= max_gap_sec
        ):
            previous.end_sec = max(
                previous.end_sec,
                segment.end_sec,
            )

        else:
            merged.append(
                segment.model_copy()
            )

    return merged


def _run_ffmpeg_clip(
    source_audio: Path,
    destination: Path,
    start_sec: float,
    end_sec: float,
) -> None:
    duration = (
        end_sec - start_sec
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(start_sec),
        "-i",
        str(source_audio),
        "-t",
        str(duration),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed while exporting "
            f"{destination.name}:\n"
            f"{result.stderr}"
        )


def export_speaker_clips(
    source_audio: str | Path,
    diarization: DiarizationResult,
    output_directory: str | Path,
    max_gap_sec: float = 0.5,
    min_duration_sec: float = 0.25,
) -> SpeakerClipManifest:

    source_audio = Path(
        source_audio
    )

    output_directory = Path(
        output_directory
    )

    if not source_audio.exists():
        raise FileNotFoundError(
            f"Audio not found: {source_audio}"
        )

    merged_segments = (
        merge_speaker_segments(
            segments=diarization.segments,
            max_gap_sec=max_gap_sec,
            min_duration_sec=min_duration_sec,
        )
    )

    clips: list[SpeakerClip] = []

    for index, segment in enumerate(
        merged_segments
    ):
        clip_id = (
            f"segment_{index:03d}_"
            f"{segment.speaker_id}"
        )

        clip_path = (
            output_directory
            / f"{clip_id}.wav"
        )

        _run_ffmpeg_clip(
            source_audio=source_audio,
            destination=clip_path,
            start_sec=segment.start_sec,
            end_sec=segment.end_sec,
        )

        clips.append(
            SpeakerClip(
                clip_id=clip_id,
                speaker_id=segment.speaker_id,
                start_sec=segment.start_sec,
                end_sec=segment.end_sec,
                clip_path=str(
                    clip_path
                ),
            )
        )

    return SpeakerClipManifest(
        audio_id=diarization.audio_id,
        source_audio=str(
            source_audio
        ),
        clips=clips,
    )


def save_speaker_clip_manifest(
    manifest: SpeakerClipManifest,
    file_path: str | Path,
) -> None:
    file_path = Path(
        file_path
    )

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        file_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            manifest.model_dump(),
            file,
            ensure_ascii=False,
            indent=2,
        )