from src.audit_policy.mapper import (
    map_answer_resolution_to_disposition,
)
from src.audit_policy.parser import load_audit_project
from src.resolver.closed_set import (
    resolve_closed_set_answer,
)
from src.resolver.models import CanonicalOption


def make_options():
    return [
        CanonicalOption(
            value="Badlapur",
            labels=["Badlapur", "बदलापुर"],
        ),
        CanonicalOption(
            value="Bijnor",
            labels=["Bijnor", "बिजनौर"],
        ),
    ]


def test_match_maps_to_asked_right():
    policy = load_audit_project(
        "configs/sample_audit_project.json"
    )

    tag_policy = policy.tags["ac_name"]

    resolution = resolve_closed_set_answer(
        raw_text="बदलापुर",
        options=make_options(),
        stored_option="Badlapur",
    )

    suggestion = map_answer_resolution_to_disposition(
        resolution=resolution,
        tag_policy=tag_policy,
    )

    assert suggestion.status == "SUGGESTED"
    assert suggestion.disposition_text == "Asked Right"
    assert suggestion.disposition_id is not None
    assert suggestion.review_required is False


def test_mismatch_maps_to_mismatch():
    policy = load_audit_project(
        "configs/sample_audit_project.json"
    )

    tag_policy = policy.tags["ac_name"]

    resolution = resolve_closed_set_answer(
        raw_text="बिजनौर",
        options=make_options(),
        stored_option="Badlapur",
    )

    suggestion = map_answer_resolution_to_disposition(
        resolution=resolution,
        tag_policy=tag_policy,
    )

    assert suggestion.status == "SUGGESTED"
    assert suggestion.disposition_text == "Mismatch"
    assert suggestion.disposition_id is not None
    assert suggestion.review_required is False


def test_uncertain_requires_human_review():
    policy = load_audit_project(
        "configs/sample_audit_project.json"
    )

    tag_policy = policy.tags["ac_name"]

    resolution = resolve_closed_set_answer(
        raw_text="कुछ समझ नहीं आया",
        options=make_options(),
        stored_option="Badlapur",
    )

    suggestion = map_answer_resolution_to_disposition(
        resolution=resolution,
        tag_policy=tag_policy,
    )

    assert suggestion.status == "UNCERTAIN"
    assert suggestion.disposition_id is None
    assert suggestion.review_required is True