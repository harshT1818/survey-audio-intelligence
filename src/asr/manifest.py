import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class ASRChunkRecord(BaseModel):
    chunk_id: str

    start_sec: float = Field(
        ge=0
    )

    end_sec: float = Field(
        gt=0
    )

    text: str

    @model_validator(mode="after")
    def validate_timing(self):
        if self.end_sec <= self.start_sec:
            raise ValueError(
                "end_sec must be greater than start_sec"
            )

        return self


class ASRManifest(BaseModel):
    audio_id: str
    model_name: str

    chunks: list[ASRChunkRecord] = Field(
        default_factory=list
    )


def load_asr_manifest(
    file_path: str | Path,
) -> ASRManifest:
    file_path = Path(file_path)

    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    return ASRManifest.model_validate(
        payload
    )


def save_asr_manifest(
    manifest: ASRManifest,
    file_path: str | Path,
) -> None:
    file_path = Path(file_path)

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