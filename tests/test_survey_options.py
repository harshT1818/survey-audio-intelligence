from src.full_sample.survey_options import (
    canonical_options_from_question,
    choice_to_canonical_option,
    primary_label,
)


def test_primary_label_candidate():
    result = primary_label(
        "हाजी रशीद अखलाक "
        "[बहुजन समाज पार्टी] "
        "<Haji Rashid Akhlaq> "
        "{Bahujan Samaj Party} "
        "*BSP*"
    )

    assert (
        result
        == "हाजी रशीद अखलाक"
    )


def test_candidate_alias_does_not_use_party_code():
    choice = {
        "option_text": (
            "हाजी रशीद अखलाक "
            "[बहुजन समाज पार्टी] "
            "<Haji Rashid Akhlaq> "
            "{Bahujan Samaj Party} "
            "*BSP*"
        ),
        "hindi": (
            "हाजी रशीद अखलाक "
            "[बहुजन समाज पार्टी]"
        ),
        "english": (
            "Haji Rashid Akhlaq "
            "[Bahujan Samaj Party]"
        ),
        "regional_language": (
            "हाजी रशीद अखलाक "
            "[बहुजन समाज पार्टी]"
        ),
        "party": "BSP",
        "dl": "BSP",
        "candidate_id": "candidate-1",
    }

    option = (
        choice_to_canonical_option(
            choice
        )
    )

    assert (
        "हाजी रशीद अखलाक"
        in option.aliases
    )

    assert (
        "Haji Rashid Akhlaq"
        in option.aliases
    )

    assert (
        "BSP"
        not in option.aliases
    )


def test_party_choice_can_use_party_code():
    choice = {
        "option_text": (
            "बहुजन समाज पार्टी "
            "[Bahujan Samaj Party] "
            "*BSP*"
        ),
        "hindi": (
            "बहुजन समाज पार्टी"
        ),
        "english": (
            "Bahujan Samaj Party"
        ),
        "regional_language": (
            "बहुजन समाज पार्टी"
        ),
        "party": "BSP",
        "dl": None,
        "candidate_id": None,
    }

    option = (
        choice_to_canonical_option(
            choice
        )
    )

    assert (
        "बहुजन समाज पार्टी"
        in option.aliases
    )

    assert (
        "Bahujan Samaj Party"
        in option.aliases
    )

    assert (
        "BSP"
        in option.aliases
    )


def test_static_question_returns_options():
    question = {
        "resolution_ready": True,
        "choice_catalog_status": (
            "STATIC"
        ),
        "choices": [
            {
                "option_text": "हाँ",
                "hindi": "हाँ",
                "english": "Yes",
                "regional_language": "हाँ",
                "party": None,
                "dl": None,
                "candidate_id": None,
            },
            {
                "option_text": "नहीं",
                "hindi": "नहीं",
                "english": "No",
                "regional_language": "नहीं",
                "party": None,
                "dl": None,
                "candidate_id": None,
            },
        ],
    }

    options = (
        canonical_options_from_question(
            question
        )
    )

    assert len(
        options
    ) == 2


def test_dynamic_placeholder_returns_no_options():
    question = {
        "resolution_ready": False,
        "choice_catalog_status": (
            "DYNAMIC_PLACEHOLDER"
        ),
        "choices": [
            {
                "option_text": "1",
                "hindi": "1",
                "english": "1",
                "regional_language": "1",
            }
        ],
    }

    options = (
        canonical_options_from_question(
            question
        )
    )

    assert options == []