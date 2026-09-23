import json
from pathlib import Path
from typing import Any

from src.ingestion.models import (
    R2AuditData,
    R2PrivateSample,
    R2SurveyData,
    R2TimingData,
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_private_r2_sample(
    sample_dir: str | Path,
    require_audio: bool = True,
) -> R2PrivateSample:

    sample_dir = Path(sample_dir)

    survey = R2SurveyData.model_validate(
        _load_json(sample_dir / "survey.json")
    )

    timing = R2TimingData.model_validate(
        _load_json(sample_dir / "timing.json")
    )

    audit = R2AuditData.model_validate(
        _load_json(sample_dir / "audit.json")
    )

    response_ids = {
        survey.response_id,
        timing.submission_id,
        audit.response_id,
    }

    if len(response_ids) != 1:
        raise ValueError(
            "Response ID mismatch between survey, "
            f"timing and audit data: {response_ids}"
        )

    if survey.project_code != audit.audit_project_code:
        raise ValueError(
            "Project code mismatch: "
            f"survey={survey.project_code}, "
            f"audit={audit.audit_project_code}"
        )

    audio_path = sample_dir / "interview.mp4"

    if require_audio and not audio_path.exists():
        raise FileNotFoundError(
            f"Missing interview audio: {audio_path}"
        )

    return R2PrivateSample(
        response_id=survey.response_id,
        project_code=survey.project_code,
        survey=survey,
        timing=timing,
        audit=audit,
        audio_path=audio_path,
    )