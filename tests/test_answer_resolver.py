from src.resolver.closed_set import (
    resolve_closed_set_answer,
)
from src.resolver.models import (
    CanonicalOption,
)


def make_options():
    return [
        CanonicalOption(
            value="Badlapur",
            labels=[
                "Badlapur",
                "बदलापुर",
            ],
        ),
        CanonicalOption(
            value="Bijnor",
            labels=[
                "Bijnor",
                "बिजनौर",
            ],
        ),
        CanonicalOption(
            value="Milak",
            labels=[
                "Milak",
                "मिलक",
            ],
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
        raw_text="I do not understand this question",
        options=make_options(),
        stored_option="Badlapur",
    )

    assert result.status == "UNCERTAIN"


def test_hindi_asr_resolves_bilingual_option():
    options = [
        CanonicalOption(
            value="Badlapur",
            labels=[
                "Badlapur",
                "बदलापुर",
                "364. बदलापुर [Badlapur]",
            ],
        ),
        CanonicalOption(
            value="Bijnor",
            labels=[
                "Bijnor",
                "बिजनौर",
            ],
        ),
    ]

    result = resolve_closed_set_answer(
        raw_text="बदलापुर",
        options=options,
        stored_option="Badlapur",
    )

    assert result.resolved_option == "Badlapur"
    assert result.status == "MATCH"


def test_pata_nahi_is_not_resolved_as_no():
    options = [
        CanonicalOption(
            value="Yes",
            labels=[
                "Yes",
                "हाँ",
                "हां",
            ],
        ),
        CanonicalOption(
            value="No",
            labels=[
                "No",
                "नहीं",
                "नही",
            ],
        ),
    ]

    result = resolve_closed_set_answer(
        raw_text="मुझे पता नहीं",
        options=options,
        stored_option="Yes",
    )

    assert result.status == "UNCERTAIN"
    assert result.resolved_option is None


def test_maloom_nahi_is_not_resolved_as_no():
    options = [
        CanonicalOption(
            value="Yes",
            labels=[
                "Yes",
                "हाँ",
            ],
        ),
        CanonicalOption(
            value="No",
            labels=[
                "No",
                "नहीं",
            ],
        ),
    ]

    result = resolve_closed_set_answer(
        raw_text="मालूम नहीं",
        options=options,
        stored_option="No",
    )

    assert result.status == "UNCERTAIN"
    assert result.resolved_option is None


def test_dont_know_is_uncertain():
    options = [
        CanonicalOption(
            value="Yes",
            labels=["Yes"],
        ),
        CanonicalOption(
            value="No",
            labels=["No"],
        ),
    ]

    result = resolve_closed_set_answer(
        raw_text="I don't know",
        options=options,
        stored_option="Yes",
    )

    assert result.status == "UNCERTAIN"
    assert result.resolved_option is None