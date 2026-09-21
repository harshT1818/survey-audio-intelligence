import pytest
from pydantic import ValidationError

from src.domain.models import SurveyAuditRequest


def test_valid_request_loads():
    payload = {
        "response_id": "sample-001",
        "project_code": "SAMPLE-PROJECT",
        "language": "hi",
        "audio_source": "samples/example.mp3",
        "questions": [
            {
                "key": "ac_name",
                "text_hi": "विधानसभा चुने",
                "type": "single_choice",
                "options": ["बिजनौर", "मिलक"],
                "selected_answer": "बिजनौर",
                "start_ms": None,
                "end_ms": None,
            }
        ],
    }

    request = SurveyAuditRequest.model_validate(payload)

    assert request.response_id == "sample-001"
    assert request.questions[0].key == "ac_name"
    assert request.questions[0].selected_answer == "बिजनौर"


def test_only_one_timing_value_fails():
    payload = {
        "response_id": "sample-001",
        "project_code": "SAMPLE-PROJECT",
        "audio_source": "samples/example.mp3",
        "questions": [
            {
                "key": "ac_name",
                "type": "single_choice",
                "start_ms": 1000,
                "end_ms": None,
            }
        ],
    }

    with pytest.raises(ValidationError):
        SurveyAuditRequest.model_validate(payload)


def test_end_before_start_fails():
    payload = {
        "response_id": "sample-001",
        "project_code": "SAMPLE-PROJECT",
        "audio_source": "samples/example.mp3",
        "questions": [
            {
                "key": "ac_name",
                "type": "single_choice",
                "start_ms": 5000,
                "end_ms": 3000,
            }
        ],
    }

    with pytest.raises(ValidationError):
        SurveyAuditRequest.model_validate(payload)