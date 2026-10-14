import re
import unicodedata
from typing import Any

from src.resolver.models import CanonicalOption


STRUCTURED_SUFFIX_PATTERN = re.compile(
    r"\s*[\[<{*].*$"
)


# How respondents commonly say party names, keyed by party code with the
# party's full Hindi name. Added only when the choice's own label is that
# party name: "Person [Party]" choices must not resolve from a party
# mention, because whether a respondent named the party or the candidate
# matters to the audit.
PARTY_SPOKEN_ALIASES = {
    "BSP": ("बहुजन समाज पार्टी", ["बसपा", "बीएसपी", "बी एस पी"]),
    "SP": ("समाजवादी पार्टी", ["सपा", "एसपी"]),
    "BJP": ("भारतीय जनता पार्टी", ["भाजपा", "बीजेपी", "बी जे पी"]),
    "RLD": ("राष्ट्रीय लोकदल", ["रालोद", "आरएलडी"]),
    "AAP": ("आम आदमी पार्टी", ["आप पार्टी"]),
}


def party_spoken_aliases(
    party: str | None,
    hindi_label: str | None,
) -> list[str]:
    entry = PARTY_SPOKEN_ALIASES.get(
        normalize_text(party).upper()
    )

    if entry is None:
        return []

    full_name, aliases = entry

    if normalize_text(hindi_label) != normalize_text(full_name):
        return []

    return aliases


def clean_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = unicodedata.normalize(
        "NFKC",
        str(value),
    )

    text = " ".join(
        text.split()
    )

    return text or None


def normalize_text(
    value: Any,
) -> str:
    text = clean_text(
        value
    )

    if text is None:
        return ""

    return text.lower()


def dedupe_texts(
    values: list[
        str | None
    ],
) -> list[str]:
    result = []
    seen = set()

    for value in values:
        cleaned = clean_text(
            value
        )

        if cleaned is None:
            continue

        key = normalize_text(
            cleaned
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            cleaned
        )

    return result


def primary_label(
    value: Any,
) -> str | None:
    """
    Extract the main answer/candidate name before structured
    metadata such as:

        Candidate [Party]
        <English Name>
        {English Party}
        *BSP*

    Examples:

        "हाजी रशीद अखलाक [बहुजन समाज पार्टी]"
            -> "हाजी रशीद अखलाक"

        "बहुजन समाज पार्टी [Bahujan Samaj Party] *BSP*"
            -> "बहुजन समाज पार्टी"
    """
    text = clean_text(
        value
    )

    if text is None:
        return None

    primary = (
        STRUCTURED_SUFFIX_PATTERN.sub(
            "",
            text,
        )
        .strip()
    )

    return primary or None


def _get(
    value: Any,
    key: str,
    default: Any = None,
) -> Any:
    if isinstance(
        value,
        dict,
    ):
        return value.get(
            key,
            default,
        )

    return getattr(
        value,
        key,
        default,
    )


def choice_to_canonical_option(
    choice: Any,
) -> CanonicalOption:
    option_text = clean_text(
        _get(
            choice,
            "option_text",
        )
    )

    if option_text is None:
        raise ValueError(
            "Survey choice has no option_text."
        )

    hindi = clean_text(
        _get(
            choice,
            "hindi",
        )
    )

    english = clean_text(
        _get(
            choice,
            "english",
        )
    )

    regional = clean_text(
        _get(
            choice,
            "regional_language",
        )
    )

    party = clean_text(
        _get(
            choice,
            "party",
        )
    )

    dl = clean_text(
        _get(
            choice,
            "dl",
        )
    )

    candidate_id = clean_text(
        _get(
            choice,
            "candidate_id",
        )
    )

    labels = dedupe_texts(
        [
            option_text,
            hindi,
            english,
            regional,
        ]
    )

    aliases = dedupe_texts(
        [
            primary_label(
                option_text
            ),
            primary_label(
                hindi
            ),
            primary_label(
                english
            ),
            primary_label(
                regional
            ),
        ]
    )

    
    # Candidate choices often have the same Party/DL value
    # across several candidates.

    # Adding "BSP" to every BSP candidate would make a simple
    # party mention appear to match several candidate options.

    # So Party/DL are aliases only for non-candidate choices.
    

    if candidate_id is None:
        aliases = dedupe_texts(
            [
                *aliases,
                party,
                dl,
                *party_spoken_aliases(
                    party,
                    primary_label(hindi)
                    or primary_label(option_text),
                ),
            ]
        )

    return CanonicalOption(
        value=option_text,
        labels=labels,
        aliases=aliases,
    )


def canonical_options_from_question(
    question: Any,
) -> list[CanonicalOption]:
    if question is None:
        return []

    resolution_ready = bool(
        _get(
            question,
            "resolution_ready",
            False,
        )
    )

    catalog_status = str(
        _get(
            question,
            "choice_catalog_status",
            "",
        )
    )

    if not resolution_ready:
        return []

    if catalog_status != "STATIC":
        return []

    choices = _get(
        question,
        "choices",
        [],
    )

    result = []

    seen_values = set()

    for choice in choices:
        option = (
            choice_to_canonical_option(
                choice
            )
        )

        key = normalize_text(
            option.value
        )

        if key in seen_values:
            continue

        seen_values.add(
            key
        )

        result.append(
            option
        )

    return result


def survey_question_map(
    survey_definition: dict[
        str,
        Any
    ],
) -> dict[str, dict[str, Any]]:
    questions = (
        survey_definition.get(
            "questions",
            []
        )
    )

    return {
        question["tag"]: question
        for question in questions
        if question.get(
            "tag"
        )
    }