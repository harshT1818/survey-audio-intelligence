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
        CanonicalOption(
            value="Milak",
            labels=["Milak", "मिलक"],
        ),
    ]


def test_exact_match():
    result = resolve_closed_set_answer(
        raw_text="Badlapur",
        options=make_options(),
        stored_option="Badlapur",
    )

    assert result.resolved_option == "Badlapur"
    assert result.status == "MATCH"


def test_minor_asr_spelling_difference():
    result = resolve_closed_set_answer(
        raw_text="Badalapur",
        options=make_options(),
        stored_option="Badlapur",
    )

    assert result.resolved_option == "Badlapur"
    assert result.status == "MATCH"


def test_mismatch():
    result = resolve_closed_set_answer(
        raw_text="Milak",
        options=make_options(),
        stored_option="Badlapur",
    )

    assert result.resolved_option == "Milak"
    assert result.status == "MISMATCH"


def test_uncertain_when_text_is_unrelated():
    result = resolve_closed_set_answer(
        raw_text="I do not know",
        options=make_options(),
        stored_option="Badlapur",
    )

    assert result.status == "UNCERTAIN"


def test_hindi_asr_resolves_bilingual_option():
    result = resolve_closed_set_answer(
        raw_text="बदलापुर",
        options=[
            CanonicalOption(
                value="Badlapur",
                labels=[
                    "बदलापुर",
                    "Badlapur",
                    "364. बदलापुर [Badlapur]",
                ],
            ),
            CanonicalOption(
                value="Bijnor",
                labels=[
                    "बिजनौर",
                    "Bijnor",
                ],
            ),
            CanonicalOption(
                value="Milak",
                labels=[
                    "मिलक",
                    "Milak",
                ],
            ),
        ],
        stored_option="Badlapur",
    )

    assert result.resolved_option == "Badlapur"
    assert result.status == "MATCH"