from pathlib import Path

from mutagen import File


def get_audio_duration_seconds(
    file_path: str | Path,
) -> float:
    audio = File(file_path)

    if audio is None or audio.info is None:
        raise ValueError(
            f"Could not detect audio format: {file_path}"
        )

    return float(audio.info.length)