import re
import unicodedata
from typing import Any

from rapidfuzz import fuzz

from src.resolver.models import (
    CanonicalOption,
)


INTERVIEWER_MARKERS = [
    "आप बताइए",
    "आप बताइये",
    "एक नाम बताइए",
    "एक नाम बताइये",
    "कौन होना चाहिए",
    "किसको देखना चाहते",
    "किसे देखना चाहते",
    "किस पार्टी",
    "कौन सी पार्टी",
    "कौनसी पार्टी",
    "बताइए",
    "बताइये",
    "कृपया स्पष्ट",
    "please tell",
    "tell me",
    "which one",
]


DIAGNOSTIC_FUZZY_THRESHOLD = 0.82


def normalize_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    text = unicodedata.normalize(
        "NFKC",
        str(value),
    )

    text = text.lower().strip()

    text = re.sub(
        r"[^\w\s\u0900-\u097F]",
        " ",
        text,
    )

    return " ".join(
        text.split()
    )


def flatten_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        str,
    ):
        return " ".join(
            value.split()
        )

    if isinstance(
        value,
        list,
    ):
        return " ".join(
            part
            for part in (
                flatten_text(
                    item
                )
                for item in value
            )
            if part
        )

    if isinstance(
        value,
        dict,
    ):
        return " ".join(
            part
            for part in (
                flatten_text(
                    item
                )
                for item
                in value.values()
            )
            if part
        )

    return str(
        value
    )


def detect_interviewer_like_text(
    text: str,
) -> list[str]:
    normalized = normalize_text(
        text
    )

    matches = []

    for marker in INTERVIEWER_MARKERS:
        normalized_marker = (
            normalize_text(
                marker
            )
        )

        if (
            normalized_marker
            and normalized_marker
            in normalized
        ):
            matches.append(
                marker
            )

    tokens = set(
        normalized.split()
    )

    has_question_shape = (
        bool(
            tokens.intersection(
                {
                    "कौन",
                    "किस",
                    "किसको",
                    "किसे",
                }
            )
        )
        and (
            "आप" in text
            or "बताइए" in text
            or "बताइये" in text
        )
    )

    if (
        has_question_shape
        and "QUESTION_SHAPE"
        not in matches
    ):
        matches.append(
            "QUESTION_SHAPE"
        )

    return matches


def option_aliases(
    option: CanonicalOption,
) -> list[str]:
    values = [
        option.value,
        *option.labels,
        *option.aliases,
    ]

    result = []
    seen = set()

    for value in values:
        cleaned = str(
            value
        ).strip()

        normalized = normalize_text(
            cleaned
        )

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        result.append(
            cleaned
        )

    return result


def text_matches_alias(
    text: str,
    alias: str,
) -> tuple[
    bool,
    float,
    str,
]:
    normalized_text = normalize_text(
        text
    )

    normalized_alias = normalize_text(
        alias
    )

    if (
        not normalized_text
        or not normalized_alias
    ):
        return (
            False,
            0.0,
            "NONE",
        )

    if (
        normalized_alias
        in normalized_text
    ):
        return (
            True,
            1.0,
            "EXACT_SUBSTRING",
        )

    # Don't fuzzy-match tiny values such as
    # हाँ, न, SP, etc.
    if len(
        normalized_alias
    ) < 4:
        return (
            False,
            0.0,
            "NONE",
        )

    score = (
        fuzz.partial_ratio(
            normalized_alias,
            normalized_text,
        )
        / 100.0
    )

    if (
        score
        >= DIAGNOSTIC_FUZZY_THRESHOLD
    ):
        return (
            True,
            round(
                score,
                4,
            ),
            "FUZZY_PARTIAL",
        )

    return (
        False,
        round(
            score,
            4,
        ),
        "NONE",
    )


def find_option_mentions(
    text: str,
    options: list[
        CanonicalOption
    ],
) -> list[dict[str, Any]]:
    result = []

    for option in options:
        best = None

        for alias in option_aliases(
            option
        ):
            (
                matched,
                score,
                match_type,
            ) = text_matches_alias(
                text=text,
                alias=alias,
            )

            if not matched:
                continue

            candidate = {
                "option_value": (
                    option.value
                ),
                "matched_alias": alias,
                "score": score,
                "match_type": (
                    match_type
                ),
            }

            if (
                best is None
                or candidate[
                    "score"
                ]
                > best[
                    "score"
                ]
            ):
                best = candidate

        if best is not None:
            result.append(
                best
            )

    result.sort(
        key=lambda item: (
            -item[
                "score"
            ],
            item[
                "option_value"
            ],
        )
    )

    return result


def resolve_stored_option(
    stored_response: Any,
    options: list[
        CanonicalOption
    ],
) -> dict[str, Any] | None:
    stored_text = normalize_text(
        flatten_text(
            stored_response
        )
    )

    if not stored_text:
        return None

    best = None

    for option in options:
        for alias in option_aliases(
            option
        ):
            normalized_alias = (
                normalize_text(
                    alias
                )
            )

            if not normalized_alias:
                continue

            if (
                stored_text
                == normalized_alias
            ):
                score = 1.0
                match_type = "EXACT"

            elif (
                normalized_alias
                in stored_text
            ):
                score = 0.99
                match_type = (
                    "CONTAINED"
                )

            elif (
                stored_text
                in normalized_alias
            ):
                score = 0.98
                match_type = (
                    "CONTAINS_STORED"
                )

            else:
                score = (
                    fuzz.WRatio(
                        stored_text,
                        normalized_alias,
                    )
                    / 100.0
                )

                match_type = "FUZZY"

            candidate = {
                "option_value": (
                    option.value
                ),
                "matched_alias": alias,
                "score": round(
                    score,
                    4,
                ),
                "match_type": (
                    match_type
                ),
            }

            if (
                best is None
                or candidate[
                    "score"
                ]
                > best[
                    "score"
                ]
            ):
                best = candidate

    if (
        best is None
        or best[
            "score"
        ] < 0.86
    ):
        return None

    return best


def selected_option_object(
    selected_match: (
        dict[str, Any]
        | None
    ),
    options: list[
        CanonicalOption
    ],
) -> CanonicalOption | None:
    if selected_match is None:
        return None

    selected_value = (
        selected_match[
            "option_value"
        ]
    )

    for option in options:
        if (
            option.value
            == selected_value
        ):
            return option

    return None


def mentions_selected_option(
    text: str,
    selected_option: (
        CanonicalOption
        | None
    ),
) -> dict[str, Any] | None:
    if selected_option is None:
        return None

    best = None

    for alias in option_aliases(
        selected_option
    ):
        (
            matched,
            score,
            match_type,
        ) = text_matches_alias(
            text=text,
            alias=alias,
        )

        if not matched:
            continue

        candidate = {
            "matched_alias": alias,
            "score": score,
            "match_type": (
                match_type
            ),
        }

        if (
            best is None
            or candidate[
                "score"
            ]
            > best[
                "score"
            ]
        ):
            best = candidate

    return best


def analyze_prompting_evaluation(
    evaluation: dict[str, Any],
    options: list[
        CanonicalOption
    ],
    stored_response: Any,
    do_not_read_options: bool,
) -> dict[str, Any]:
    """
    Diagnose only the evidence actually selected by
    evaluate_prompting_dialogue().

    Pre-anchor dialogue cannot create role conflicts here.
    """
    anchor = evaluation.get(
        "anchor_agent_turn"
    )

    respondent = evaluation.get(
        "initial_respondent_turn"
    )

    followups = evaluation.get(
        "agent_followup_turns",
        [],
    )

    selected_match = (
        resolve_stored_option(
            stored_response=(
                stored_response
            ),
            options=options,
        )
    )

    selected_option = (
        selected_option_object(
            selected_match=(
                selected_match
            ),
            options=options,
        )
    )

    safety_flags = []
    observations = []
    role_conflicts = []

    prediction = evaluation.get(
        "prediction"
    )

    anchor_score = evaluation.get(
        "anchor_similarity"
    )

    if anchor is None:
        safety_flags.append(
            "NO_SAFE_QUESTION_ANCHOR"
        )

    if (
        anchor_score is not None
        and anchor_score < 0.70
    ):
        safety_flags.append(
            "LOW_CONFIDENCE_QUESTION_ANCHOR"
        )

    if respondent is None:
        safety_flags.append(
            "NO_USABLE_RESPONDENT_AFTER_ANCHOR"
        )

    respondent_selected = None

    if respondent is not None:
        respondent_text = str(
            respondent.get(
                "transcript",
                "",
            )
        )

        markers = (
            detect_interviewer_like_text(
                respondent_text
            )
        )

        if markers:
            role_conflicts.append(
                {
                    "role": "respondent",
                    "speaker_id": (
                        respondent.get(
                            "speaker_id"
                        )
                    ),
                    "start_sec": (
                        respondent.get(
                            "start_sec"
                        )
                    ),
                    "end_sec": (
                        respondent.get(
                            "end_sec"
                        )
                    ),
                    "transcript": (
                        respondent_text
                    ),
                    "markers": markers,
                }
            )

            safety_flags.append(
                "RESPONDENT_ROLE_CONFLICT"
            )

        respondent_selected = (
            mentions_selected_option(
                text=respondent_text,
                selected_option=(
                    selected_option
                ),
            )
        )

        if respondent_selected:
            observations.append(
                "RESPONDENT_MENTIONED_STORED_ANSWER"
            )

    agent_option_turns = []
    selected_agent_mentions = []

    distinct_agent_options = set()

    for turn in followups:
        text = str(
            turn.get(
                "transcript",
                "",
            )
        )

        mentions = (
            find_option_mentions(
                text=text,
                options=options,
            )
        )

        for mention in mentions:
            distinct_agent_options.add(
                mention[
                    "option_value"
                ]
            )

        if mentions:
            agent_option_turns.append(
                {
                    "start_sec": (
                        turn.get(
                            "start_sec"
                        )
                    ),
                    "end_sec": (
                        turn.get(
                            "end_sec"
                        )
                    ),
                    "transcript": text,
                    "cross_speaker_overlap": bool(
                        turn.get(
                            "cross_speaker_overlap",
                            False,
                        )
                    ),
                    "mentions": mentions,
                }
            )

        selected_mention = (
            mentions_selected_option(
                text=text,
                selected_option=(
                    selected_option
                ),
            )
        )

        if selected_mention:
            selected_agent_mentions.append(
                {
                    "start_sec": (
                        turn.get(
                            "start_sec"
                        )
                    ),
                    "end_sec": (
                        turn.get(
                            "end_sec"
                        )
                    ),
                    "transcript": text,
                    "cross_speaker_overlap": bool(
                        turn.get(
                            "cross_speaker_overlap",
                            False,
                        )
                    ),
                    **selected_mention,
                }
            )

            markers = (
                detect_interviewer_like_text(
                    text
                )
            )

            if markers:
                observations.append(
                    "AGENT_DIRECTIVE_AND_STORED_ANSWER_SAME_TURN"
                )

    if selected_agent_mentions:
        observations.append(
            "AGENT_MENTIONED_STORED_ANSWER"
        )

    if (
        selected_agent_mentions
        and not respondent_selected
    ):
        safety_flags.append(
            "SELECTED_ANSWER_AGENT_ONLY"
        )

    if any(
        item[
            "cross_speaker_overlap"
        ]
        for item
        in selected_agent_mentions
    ):
        safety_flags.append(
            "DECISIVE_OPTION_MENTION_OVERLAPS_SPEAKERS"
        )

    if (
        do_not_read_options
        and len(
            distinct_agent_options
        ) >= 2
    ):
        observations.append(
            "AGENT_ENUMERATED_OPTIONS_ON_DNR_QUESTION"
        )

    elif (
        do_not_read_options
        and len(
            distinct_agent_options
        ) == 1
    ):
        observations.append(
            "AGENT_MENTIONED_OPTION_ON_DNR_QUESTION"
        )

    if (
        prediction
        == "INSUFFICIENT_ROLE_EVIDENCE"
    ):
        safety_flags.append(
            "INSUFFICIENT_DECISION_EVIDENCE"
        )

    safety_flags = list(
        dict.fromkeys(
            safety_flags
        )
    )

    observations = list(
        dict.fromkeys(
            observations
        )
    )

    evidence_safety = (
        "REVIEW"
        if safety_flags
        else "SAFE_FOR_PROMPTING_RULES"
    )

    return {
        "evidence_safety": (
            evidence_safety
        ),
        "safety_flags": (
            safety_flags
        ),
        "observations": (
            observations
        ),
        "anchor_method": (
            evaluation.get(
                "anchor_method"
            )
        ),
        "anchor_similarity": (
            evaluation.get(
                "anchor_similarity"
            )
        ),
        "anchor_agent_turn": (
            anchor
        ),
        "initial_respondent_turn": (
            respondent
        ),
        "followup_turn_count": (
            len(
                followups
            )
        ),
        "role_conflicts": (
            role_conflicts
        ),
        "selected_option_match": (
            selected_match
        ),
        "respondent_selected_mention": (
            respondent_selected
        ),
        "selected_agent_mentions": (
            selected_agent_mentions
        ),
        "agent_option_turns": (
            agent_option_turns
        ),
        "distinct_agent_option_count": (
            len(
                distinct_agent_options
            )
        ),
    }