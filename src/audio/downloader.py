from pathlib import Path

import requests


AUDIO_BASE_URL = (
    "https://survey-audios.s3.ap-south-1.amazonaws.com"
)


def build_audio_url(response_id: str) -> str:
    return f"{AUDIO_BASE_URL}/{response_id}.mp3"


def download_audio(
    response_id: str,
    output_path: str | Path,
    overwrite: bool = False,
) -> Path:
    output_path = Path(output_path)

    if output_path.exists() and not overwrite:
        return output_path

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    url = build_audio_url(response_id)

    with requests.get(
        url,
        stream=True,
        timeout=60,
    ) as response:
        response.raise_for_status()

        with output_path.open("wb") as file:
            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk:
                    file.write(chunk)

    return output_path