import re
import unicodedata
from typing import Any

from rapidfuzz import fuzz

from src.prompting.rules import (
    detect_prompting,
)
from src.resolver.models import (
    CanonicalOption,
)


OPTION_CONTAINER_KEYS = {
    "options",
    "option",
    "choices",
    "choice",
    "answer_options",
    "answeroptions",
    "question_options",
    "questionoptions",
}


TEXT_FIELDS = [
    "value",
    "answer",
    "label",
    "text",
    "name",
    "english_value",
    "englishVal",
    "hindi_value",
    "hindiVal",
    "regional_value",
    "regionalVal",
]


MIN_QUESTION_ANCHOR_SCORE = 0.60


DO_NOT_READ_PATTERN = re.compile(
    r"DO\s*NOT\s*READ\s*THE\s*OPTIONS",
    flags=re.IGNORECASE,
)


NOTE_PATTERN = re.compile(
    r"\[\s*Note\s*:[^\]]*\]",
    flags=re.IGNORECASE,
)


DYNAMIC_REFERENCE_PATTERN = re.compile(
    r"\$#[A-Za-z0-9_]+-[A-Za-z0-9_]+"
)


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
        r"\s+",
        " ",
        text,
    )

    return text


def normalize_for_similarity(
    value: Any,
) -> str:
    text = normalize_text(
        value
    )

    text = (
        DYNAMIC_REFERENCE_PATTERN.sub(
            " ",
            text,
        )
    )

    text = NOTE_PATTERN.sub(
        " ",
        text,
    )

    match = DO_NOT_READ_PATTERN.search(
        text
    )

    if match:
        text = text[
            :match.start()
        ]

    text = re.sub(
        r"[^\w\s\u0900-\u097F]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def flatten_strings(
    value: Any,
) -> list[str]:
    result = []

    if isinstance(
        value,
        str,
    ):
        cleaned = " ".join(
            value.split()
        )

        if cleaned:
            result.append(
                cleaned
            )

        return result

    if isinstance(
        value,
        list,
    ):
        for item in value:
            result.extend(
                flatten_strings(
                    item
                )
            )

        return result

    if isinstance(
        value,
        dict,
    ):
        for item in value.values():
            result.extend(
                flatten_strings(
                    item
                )
            )

    return result


def infer_human_prompting_label(
    value: Any,
) -> str:
    """
    Convert human Audit CRM disposition data into a
    coarse prompting label.

    NO_PROMPTING is deliberately checked first because
    values such as "No Prompting Done" contain the word
    "Prompting".
    """
    texts = flatten_strings(
        value
    )

    combined = normalize_text(
        " | ".join(
            texts
        )
    )

    no_prompting_markers = [
        "no prompting",
        "without prompting",
        "no-prompting",
    ]

    if any(
        marker in combined
        for marker
        in no_prompting_markers
    ):
        return "NO_PROMPTING"

    if "prompting" in combined:
        return "PROMPTING"

    return "UNKNOWN"


def find_policy_entry(
    policy: list[
        dict[str, Any]
    ],
    tag: str,
) -> dict[str, Any] | None:
    for entry in policy:
        if entry.get(
            "tag"
        ) == tag:
            return entry

    return None


def _option_texts_from_item(
    item: Any,
) -> list[str]:
    if isinstance(
        item,
        str,
    ):
        cleaned = " ".join(
            item.split()
        )

        return (
            [cleaned]
            if cleaned
            else []
        )

    if not isinstance(
        item,
        dict,
    ):
        return []

    values = []

    for field in TEXT_FIELDS:
        field_value = item.get(
            field
        )

        values.extend(
            flatten_strings(
                field_value
            )
        )

    if values:
        return list(
            dict.fromkeys(
                values
            )
        )

    return []


def _collect_option_containers(
    node: Any,
) -> list[Any]:
    containers = []

    if isinstance(
        node,
        dict,
    ):
        for key, value in node.items():
            normalized_key = (
                normalize_text(
                    key
                )
                .replace(
                    " ",
                    "_",
                )
            )

            if (
                normalized_key
                in OPTION_CONTAINER_KEYS
                and isinstance(
                    value,
                    (list, dict),
                )
            ):
                containers.append(
                    value
                )

            if isinstance(
                value,
                (dict, list),
            ):
                containers.extend(
                    _collect_option_containers(
                        value
                    )
                )

    elif isinstance(
        node,
        list,
    ):
        for item in node:
            containers.extend(
                _collect_option_containers(
                    item
                )
            )

    return containers


def extract_canonical_options(
    policy_entry: (
        dict[str, Any]
        | None
    ),
) -> list[CanonicalOption]:
    """
    Legacy Audit CRM extraction helper.

    raw_response is deliberately NOT used as a source
    of possible options because it contains the already
    selected answer and would bias prompting detection.

    Real SurveyXpress choices should now normally come
    from survey_definition.json via survey_options.py.
    """
    if not policy_entry:
        return []

    data = policy_entry.get(
        "data"
    )

    if not isinstance(
        data,
        dict,
    ):
        return []

    containers = (
        _collect_option_containers(
            data
        )
    )

    extracted: list[
        CanonicalOption
    ] = []

    seen = set()

    for container in containers:
        items = []

        if isinstance(
            container,
            list,
        ):
            items = container

        elif isinstance(
            container,
            dict,
        ):
            items = list(
                container.values()
            )

        for item in items:
            texts = (
                _option_texts_from_item(
                    item
                )
            )

            if not texts:
                continue

            canonical_value = (
                texts[0]
            )

            normalized_value = (
                normalize_text(
                    canonical_value
                )
            )

            if not normalized_value:
                continue

            if normalized_value in seen:
                continue

            seen.add(
                normalized_value
            )

            extracted.append(
                CanonicalOption(
                    value=canonical_value,
                    labels=texts,
                    aliases=[],
                )
            )

    return extracted


def _usable_turns(
    dialogue: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        turn
        for turn
        in dialogue.get(
            "turns",
            [],
        )
        if (
            turn.get(
                "asr_status"
            )
            == "COMPLETE"
            and str(
                turn.get(
                    "transcript",
                    "",
                )
            ).strip()
        )
    ]


def question_turn_similarity(
    question_text: str,
    transcript: str,
) -> float:
    """
    Compare an ASR agent turn against the actual survey
    question.

    partial_ratio helps when the spoken question is noisy
    or shortened.

    token_set_ratio rewards shared meaningful words while
    being less sensitive to ordering / filler.
    """
    question = (
        normalize_for_similarity(
            question_text
        )
    )

    spoken = (
        normalize_for_similarity(
            transcript
        )
    )

    if not question or not spoken:
        return 0.0

    partial = (
        fuzz.partial_ratio(
            question,
            spoken,
        )
        / 100.0
    )

    token_set = (
        fuzz.token_set_ratio(
            question,
            spoken,
        )
        / 100.0
    )

    score = (
        0.75 * partial
        + 0.25 * token_set
    )

    return round(
        score,
        4,
    )


def select_question_anchor(
    dialogue: dict[str, Any],
    question_window: dict[str, Any],
) -> dict[str, Any]:
    usable = _usable_turns(
        dialogue
    )

    question_start = float(
        question_window.get(
            "start_sec",
            0.0,
        )
    )

    raw_end = (
        question_window.get(
            "end_sec"
        )
    )

    question_end = (
        float(raw_end)
        if raw_end is not None
        else None
    )

    agent_turns = [
        turn
        for turn in usable
        if (
            turn.get(
                "role"
            )
            == "agent"
            and float(
                turn.get(
                    "start_sec",
                    0.0,
                )
            )
            >= (
                question_start
                - 0.25
            )
            and (
                question_end is None
                or float(
                    turn.get(
                        "start_sec",
                        0.0,
                    )
                )
                <= (
                    question_end
                    + 0.50
                )
            )
        )
    ]

    if not agent_turns:
        return {
            "turn": None,
            "score": None,
            "method": (
                "NO_AGENT_TURN"
            ),
            "candidates": [],
        }

    question_text = str(
        dialogue.get(
            "question_text"
        )
        or question_window.get(
            "question_text"
        )
        or ""
    ).strip()

    if not question_text:
        first = agent_turns[0]

        return {
            "turn": first,
            "score": None,
            "method": (
                "FIRST_AGENT_FALLBACK"
            ),
            "candidates": [],
        }

    scored = []

    for turn in agent_turns:
        score = (
            question_turn_similarity(
                question_text=(
                    question_text
                ),
                transcript=str(
                    turn.get(
                        "transcript",
                        "",
                    )
                ),
            )
        )

        scored.append(
            {
                "turn": turn,
                "score": score,
            }
        )

    scored.sort(
        key=lambda item: (
            -item[
                "score"
            ],
            float(
                item[
                    "turn"
                ].get(
                    "start_sec",
                    0.0,
                )
            ),
        )
    )

    candidates = [
        {
            "turn_index": (
                item[
                    "turn"
                ].get(
                    "turn_index"
                )
            ),
            "start_sec": (
                item[
                    "turn"
                ].get(
                    "start_sec"
                )
            ),
            "end_sec": (
                item[
                    "turn"
                ].get(
                    "end_sec"
                )
            ),
            "score": (
                item[
                    "score"
                ]
            ),
            "transcript": (
                item[
                    "turn"
                ].get(
                    "transcript"
                )
            ),
        }
        for item
        in scored[:3]
    ]

    best = scored[0]

    if (
        best["score"]
        < MIN_QUESTION_ANCHOR_SCORE
    ):
        return {
            "turn": None,
            "score": (
                best[
                    "score"
                ]
            ),
            "method": (
                "QUESTION_TEXT_LOW_SIMILARITY"
            ),
            "candidates": candidates,
        }

    return {
        "turn": (
            best["turn"]
        ),
        "score": (
            best["score"]
        ),
        "method": (
            "QUESTION_TEXT_SIMILARITY"
        ),
        "candidates": candidates,
    }


def _base_result(
    prediction: str,
    review_required: bool,
    reason: str,
    *,
    detector_result: Any = None,
    anchor_agent_turn: Any = None,
    initial_respondent_turn: Any = None,
    agent_followup_turns: (
        list[dict[str, Any]]
        | None
    ) = None,
    anchor_similarity: (
        float
        | None
    ) = None,
    anchor_method: (
        str
        | None
    ) = None,
    anchor_candidates: (
        list[dict[str, Any]]
        | None
    ) = None,
) -> dict[str, Any]:
    return {
        "prediction": prediction,
        "review_required": (
            review_required
        ),
        "reason": reason,
        "detector_result": (
            detector_result
        ),
        "anchor_agent_turn": (
            anchor_agent_turn
        ),
        "initial_respondent_turn": (
            initial_respondent_turn
        ),
        "agent_followup_turns": (
            agent_followup_turns
            or []
        ),
        "anchor_similarity": (
            anchor_similarity
        ),
        "anchor_method": (
            anchor_method
        ),
        "anchor_candidates": (
            anchor_candidates
            or []
        ),
    }


def evaluate_prompting_dialogue(
    dialogue: dict[str, Any],
    question_window: dict[str, Any],
    options: list[
        CanonicalOption
    ],
) -> dict[str, Any]:
    """
    Adapt real role-labelled dialogue to the existing
    detect_prompting() interface.

    Important safety rule:
    the question anchor is selected by similarity to the
    actual SurveyXpress question text, not merely by taking
    the first agent speech in the question time window.

    Flow:

        survey question text
        -> best matching usable agent turn
        -> first usable respondent after that anchor
        -> subsequent agent speech
        -> existing prompting detector

    Missing respondent speech is never invented.
    """
    if (
        dialogue.get(
            "evidence_status"
        )
        != "ROLE_DIALOGUE_AVAILABLE"
    ):
        return _base_result(
            prediction=(
                "INSUFFICIENT_ROLE_EVIDENCE"
            ),
            review_required=True,
            reason=(
                "Both usable agent and respondent "
                "speech were not available."
            ),
        )

    usable = _usable_turns(
        dialogue
    )

    anchor_result = (
        select_question_anchor(
            dialogue=dialogue,
            question_window=(
                question_window
            ),
        )
    )

    anchor_agent = (
        anchor_result[
            "turn"
        ]
    )

    if anchor_agent is None:
        if (
            anchor_result[
                "method"
            ]
            == (
                "QUESTION_TEXT_LOW_SIMILARITY"
            )
        ):
            reason = (
                "Agent speech was available, but no "
                "turn matched the SurveyXpress "
                "question strongly enough to use as "
                "a safe question anchor."
            )
        else:
            reason = (
                "No usable agent question turn "
                "was found for this survey "
                "question."
            )

        return _base_result(
            prediction=(
                "INSUFFICIENT_ROLE_EVIDENCE"
            ),
            review_required=True,
            reason=reason,
            anchor_similarity=(
                anchor_result[
                    "score"
                ]
            ),
            anchor_method=(
                anchor_result[
                    "method"
                ]
            ),
            anchor_candidates=(
                anchor_result[
                    "candidates"
                ]
            ),
        )

    respondent_turns = [
        turn
        for turn in usable
        if turn.get(
            "role"
        ) == "respondent"
    ]

    agent_turns = [
        turn
        for turn in usable
        if turn.get(
            "role"
        ) == "agent"
    ]

    anchor_end = float(
        anchor_agent[
            "end_sec"
        ]
    )

    initial_respondent = next(
        (
            turn
            for turn
            in respondent_turns
            if float(
                turn[
                    "start_sec"
                ]
            )
            >= (
                anchor_end
                - 0.15
            )
        ),
        None,
    )

    if initial_respondent is None:
        return _base_result(
            prediction=(
                "INSUFFICIENT_ROLE_EVIDENCE"
            ),
            review_required=True,
            reason=(
                "No usable respondent speech "
                "was recovered after the matched "
                "agent question turn."
            ),
            anchor_agent_turn=(
                anchor_agent
            ),
            anchor_similarity=(
                anchor_result[
                    "score"
                ]
            ),
            anchor_method=(
                anchor_result[
                    "method"
                ]
            ),
            anchor_candidates=(
                anchor_result[
                    "candidates"
                ]
            ),
        )

    respondent_end = float(
        initial_respondent[
            "end_sec"
        ]
    )

    followups = [
        turn
        for turn in agent_turns
        if float(
            turn[
                "start_sec"
            ]
        )
        >= (
            respondent_end
            - 0.15
        )
    ]

    respondent_text = str(
        initial_respondent[
            "transcript"
        ]
    )

    agent_followup_text = (
        " ".join(
            str(
                turn[
                    "transcript"
                ]
            )
            for turn in followups
            if str(
                turn.get(
                    "transcript",
                    "",
                )
            ).strip()
        )
    )

    detector = detect_prompting(
        respondent_text=(
            respondent_text
        ),
        agent_followup_text=(
            agent_followup_text
        ),
        options=options,
    )

    common = {
        "detector_result": (
            detector.model_dump()
        ),
        "anchor_agent_turn": (
            anchor_agent
        ),
        "initial_respondent_turn": (
            initial_respondent
        ),
        "agent_followup_turns": (
            followups
        ),
        "anchor_similarity": (
            anchor_result[
                "score"
            ]
        ),
        "anchor_method": (
            anchor_result[
                "method"
            ]
        ),
        "anchor_candidates": (
            anchor_result[
                "candidates"
            ]
        ),
    }

    if (
        initial_respondent.get(
            "cross_speaker_overlap"
        )
        and detector.status
        == "PROMPTING_EVIDENCE"
    ):
        return _base_result(
            prediction="UNCERTAIN",
            review_required=True,
            reason=(
                "Prompting-like evidence was "
                "detected, but the initial "
                "respondent turn overlaps another "
                "speaker and is unsafe for "
                "automatic classification."
            ),
            **common,
        )

    if (
        detector.status
        == "PROMPTING_EVIDENCE"
    ):
        prediction = "PROMPTING"

    elif (
        detector.status
        == "NO_PROMPTING_EVIDENCE"
    ):
        prediction = (
            "NO_PROMPTING"
        )

    else:
        prediction = "UNCERTAIN"

    return _base_result(
        prediction=prediction,
        review_required=(
            detector.review_required
        ),
        reason=detector.reason,
        **common,
    )


def compare_prompting_prediction(
    prediction: str,
    human_label: str,
) -> bool | None:
    if prediction not in {
        "PROMPTING",
        "NO_PROMPTING",
    }:
        return None

    if human_label not in {
        "PROMPTING",
        "NO_PROMPTING",
    }:
        return None

    return (
        prediction
        == human_label
    )