from dataclasses import dataclass


@dataclass
class TranscriptSegment:
    start_sec: float | None
    end_sec: float | None
    text: str


@dataclass
class TranscriptionResult:
    model_name: str
    text: str
    segments: list[TranscriptSegment]