import re
import unicodedata
from typing import Any

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
    Convert the human Audit CRM disposition payload into
    a coarse prompting label.

    We intentionally check NO_PROMPTING before PROMPTING
    because strings such as "No Prompting Done" still
    contain the word "Prompting".
    """
    texts = flatten_strings(
        value
    )

    combined = normalize_text(
        " | ".join(texts)
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
            dict.fromkeys(values)
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
                normalize_text(key)
                .replace(" ", "_")
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
    Extract options only from explicit option/choice
    containers inside policy `data`.

    raw_response is deliberately NOT used as an option
    source, because using the already-selected answer as
    the only possible option would bias prompting detection.
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


def evaluate_prompting_dialogue(
    dialogue: dict[str, Any],
    question_window: dict[str, Any],
    options: list[
        CanonicalOption
    ],
) -> dict[str, Any]:
    """
    Adapt a real role-labelled dialogue to the existing
    detect_prompting() interface.

    We do not invent missing respondent speech.

    Flow:
        question starts
        -> first usable agent turn
        -> first usable respondent turn
        -> any later usable agent speech becomes follow-up

    If the respondent is not recoverable from ASR after the
    question begins, classification is withheld.
    """
    if (
        dialogue.get(
            "evidence_status"
        )
        != "ROLE_DIALOGUE_AVAILABLE"
    ):
        return {
            "prediction": (
                "INSUFFICIENT_ROLE_EVIDENCE"
            ),
            "review_required": True,
            "reason": (
                "Both usable agent and respondent "
                "speech were not available."
            ),
            "detector_result": None,
            "anchor_agent_turn": None,
            "initial_respondent_turn": None,
            "agent_followup_turns": [],
        }

    question_start = float(
        question_window[
            "start_sec"
        ]
    )

    usable = _usable_turns(
        dialogue
    )

    agent_turns = [
        turn
        for turn in usable
        if turn.get(
            "role"
        ) == "agent"
    ]

    respondent_turns = [
        turn
        for turn in usable
        if turn.get(
            "role"
        ) == "respondent"
    ]

    anchor_agent = next(
        (
            turn
            for turn in agent_turns
            if float(
                turn["start_sec"]
            )
            >= (
                question_start
                - 0.05
            )
        ),
        None,
    )

    if anchor_agent is None:
        return {
            "prediction": (
                "INSUFFICIENT_ROLE_EVIDENCE"
            ),
            "review_required": True,
            "reason": (
                "No usable agent question turn "
                "was found after the survey "
                "question start."
            ),
            "detector_result": None,
            "anchor_agent_turn": None,
            "initial_respondent_turn": None,
            "agent_followup_turns": [],
        }

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
                turn["start_sec"]
            )
            >= (
                anchor_end
                - 0.15
            )
        ),
        None,
    )

    if initial_respondent is None:
        return {
            "prediction": (
                "INSUFFICIENT_ROLE_EVIDENCE"
            ),
            "review_required": True,
            "reason": (
                "No usable respondent speech "
                "was recovered after the agent "
                "question turn."
            ),
            "detector_result": None,
            "anchor_agent_turn": (
                anchor_agent
            ),
            "initial_respondent_turn": None,
            "agent_followup_turns": [],
        }

    respondent_end = float(
        initial_respondent[
            "end_sec"
        ]
    )

    followups = [
        turn
        for turn in agent_turns
        if float(
            turn["start_sec"]
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
                turn["transcript"]
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

    if (
        initial_respondent.get(
            "cross_speaker_overlap"
        )
        and detector.status
        == "PROMPTING_EVIDENCE"
    ):
        return {
            "prediction": "UNCERTAIN",
            "review_required": True,
            "reason": (
                "Prompting-like evidence was "
                "detected, but the initial "
                "respondent turn overlaps another "
                "speaker and is unsafe for "
                "automatic classification."
            ),
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
        }

    if (
        detector.status
        == "PROMPTING_EVIDENCE"
    ):
        prediction = "PROMPTING"

    elif (
        detector.status
        == "NO_PROMPTING_EVIDENCE"
    ):
        prediction = "NO_PROMPTING"

    else:
        prediction = "UNCERTAIN"

    return {
        "prediction": prediction,
        "review_required": (
            detector.review_required
        ),
        "reason": detector.reason,
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
    }


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