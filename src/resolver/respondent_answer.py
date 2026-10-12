"""Deterministic resolution of a respondent's spoken answer.

Order: whole-answer option match, then a unique option mention inside a
statement, then a small spoken number. Mention and number results use
RULE_CONFIDENCE, which sits between the evidence gate's prefill (0.72)
and auto-fill (0.90) thresholds, so they can only ever be prefilled.
"""

import re
import unicodedata
from collections import defaultdict

from src.resolver.closed_set import (
    comparison_status,
    is_uncertain_response,
    resolve_closed_set_answer,
)
from src.resolver.models import AnswerResolution, CanonicalOption


RULE_CONFIDENCE = 0.80

NEGATION_TOKENS = {"नहीं", "नही", "ना", "न", "मत"}

# "या" offers alternatives ("या तो X हो या Y"), usually echoing the
# interviewer; a mention inside it is not a choice.
ALTERNATIVE_TOKENS = {"या"}

# Titles shared across many names; never distinctive on their own.
HONORIFIC_TOKENS = {"हाजी", "मो", "मोहम्मद", "डॉ", "डा", "श्री", "श्रीमती", "कुमार", "सिंह"}

MIN_SKELETON_LENGTH = 3

# Stored numeric answers above this are identifiers (phone numbers),
# never compared with a spoken number.
MAX_SMALL_NUMBER = 120

DEVANAGARI_MARKS = re.compile(r"[ऀ-ःऺ-ॏ॑-ॗॢॣ]")
NON_DEVANAGARI = re.compile(r"[^ऀ-ॿ\s]")

HINDI_NUMBERS = {
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6,
    "सात": 7, "आठ": 8, "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12, "तेरह": 13,
    "चौदह": 14, "पंद्रह": 15, "पन्द्रह": 15, "सोलह": 16, "सत्रह": 17, "अठारह": 18,
    "उन्नीस": 19, "बीस": 20, "इक्कीस": 21, "बाईस": 22, "तेईस": 23, "चौबीस": 24,
    "पच्चीस": 25, "छब्बीस": 26, "सत्ताईस": 27, "अट्ठाईस": 28, "अठाईस": 28,
    "उनतीस": 29, "तीस": 30, "इकतीस": 31, "बत्तीस": 32, "तैंतीस": 33, "चौंतीस": 34,
    "पैंतीस": 35, "छत्तीस": 36, "सैंतीस": 37, "अड़तीस": 38, "उनतालीस": 39,
    "चालीस": 40, "इकतालीस": 41, "बयालीस": 42, "तैंतालीस": 43, "चवालीस": 44,
    "चौवालीस": 44, "पैंतालीस": 45, "छियालीस": 46, "सैंतालीस": 47, "अड़तालीस": 48,
    "उनचास": 49, "पचास": 50, "इक्यावन": 51, "बावन": 52, "तिरेपन": 53, "तिरपन": 53,
    "चौवन": 54, "चव्वन": 54, "पचपन": 55, "छप्पन": 56, "सत्तावन": 57, "अट्ठावन": 58,
    "अठावन": 58, "उनसठ": 59, "साठ": 60, "इकसठ": 61, "बासठ": 62, "तिरसठ": 63,
    "चौंसठ": 64, "पैंसठ": 65, "छियासठ": 66, "सड़सठ": 67, "सरसठ": 67, "अड़सठ": 68,
    "उनहत्तर": 69, "सत्तर": 70, "इकहत्तर": 71, "बहत्तर": 72, "तिहत्तर": 73,
    "चौहत्तर": 74, "पचहत्तर": 75, "छिहत्तर": 76, "सतहत्तर": 77, "अठहत्तर": 78,
    "उन्यासी": 79, "उनासी": 79, "अस्सी": 80, "इक्यासी": 81, "बयासी": 82,
    "तिरासी": 83, "चौरासी": 84, "पचासी": 85, "छियासी": 86, "सत्तासी": 87,
    "अट्ठासी": 88, "नवासी": 89, "नब्बे": 90, "इक्यानवे": 91, "बानवे": 92,
    "तिरानवे": 93, "तिरानबे": 93, "चौरानवे": 94, "पचानवे": 95, "छियानवे": 96,
    "सत्तानवे": 97, "अट्ठानवे": 98, "निन्यानवे": 99, "सौ": 100,
}


def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text or "")
    text = re.sub(r"[^\w\sऀ-ॿ]", " ", text)
    return text.split()


def skeleton(token: str) -> str:
    """Consonant skeleton: drops vowel signs, nukta and nasal marks, so
    spelling variants such as राशिद / रशीद both become रशद."""
    token = unicodedata.normalize("NFD", token)
    token = DEVANAGARI_MARKS.sub("", token)
    token = NON_DEVANAGARI.sub("", token)
    return unicodedata.normalize("NFC", token)


def _turn_skeletons(tokens: list[str]) -> set[str]:
    # Joined neighbours catch ASR word splits ("बस पा" for "बसपा").
    words = [skeleton(token) for token in tokens]
    joined = [a + b for a, b in zip(words, words[1:])]
    return {word for word in words + joined if len(word) >= MIN_SKELETON_LENGTH}


def distinctive_skeletons(options: list[CanonicalOption]) -> dict[str, set[str]]:
    """Per option, Devanagari name words that occur in no other option."""
    per_option: dict[str, set[str]] = {}
    owners: dict[str, set[str]] = defaultdict(set)

    for option in options:
        words = set()
        for text in [option.value, *option.labels, *option.aliases]:
            for token in _tokens(text):
                if token in HONORIFIC_TOKENS:
                    continue
                word = skeleton(token)
                if len(word) >= MIN_SKELETON_LENGTH:
                    words.add(word)
        per_option[option.value] = words
        for word in words:
            owners[word].add(option.value)

    return {
        value: {word for word in words if len(owners[word]) == 1}
        for value, words in per_option.items()
    }


def _uncertain(raw_text: str, stored_option: str | None, confidence: float = 0.0):
    return AnswerResolution(
        raw_text=raw_text,
        stored_option=stored_option,
        status="UNCERTAIN",
        confidence=confidence,
    )


def _has_guard_token(tokens: list[str]) -> bool:
    return bool(set(tokens) & (NEGATION_TOKENS | ALTERNATIVE_TOKENS))


def resolve_unique_mention(
    raw_text: str,
    options: list[CanonicalOption],
    stored_option: str | None = None,
) -> AnswerResolution:
    tokens = _tokens(raw_text)
    if not tokens or not options or is_uncertain_response(raw_text) or _has_guard_token(tokens):
        return _uncertain(raw_text, stored_option)

    turn = _turn_skeletons(tokens)
    matched = [
        value
        for value, words in distinctive_skeletons(options).items()
        if words & turn
    ]

    if len(matched) != 1:
        return _uncertain(raw_text, stored_option)

    return AnswerResolution(
        raw_text=raw_text,
        resolved_option=matched[0],
        stored_option=stored_option,
        status=comparison_status(matched[0], stored_option),
        confidence=RULE_CONFIDENCE,
    )


def spoken_numbers(raw_text: str) -> list[int]:
    numbers = []
    for token in _tokens(raw_text):
        if token.isdigit():
            numbers.append(int(token))
        elif token in HINDI_NUMBERS:
            numbers.append(HINDI_NUMBERS[token])
    return numbers


def _small_stored_number(stored_option: str | None) -> int | None:
    digits = re.sub(r"\D", "", str(stored_option or ""))
    if not digits or len(digits) > 3:
        return None
    value = int(digits)
    return value if 0 < value <= MAX_SMALL_NUMBER else None


def resolve_small_number(
    raw_text: str,
    stored_option: str | None,
) -> AnswerResolution:
    stored = _small_stored_number(stored_option)
    tokens = _tokens(raw_text)
    if stored is None or is_uncertain_response(raw_text) or _has_guard_token(tokens):
        return _uncertain(raw_text, stored_option)

    numbers = set(spoken_numbers(raw_text))
    if len(numbers) != 1:
        return _uncertain(raw_text, stored_option)

    value = numbers.pop()
    return AnswerResolution(
        raw_text=raw_text,
        resolved_option=str(value),
        stored_option=stored_option,
        status="MATCH" if value == stored else "MISMATCH",
        confidence=RULE_CONFIDENCE,
    )


def resolve_respondent_answer(
    raw_text: str,
    options: list[CanonicalOption],
    stored_option: str | None = None,
) -> AnswerResolution:
    whole = resolve_closed_set_answer(
        raw_text=raw_text,
        options=options,
        stored_option=stored_option,
        require_whole_answer=True,
    )
    if whole.status != "UNCERTAIN" or not raw_text.strip():
        return whole

    if options:
        mention = resolve_unique_mention(raw_text, options, stored_option)
    else:
        mention = resolve_small_number(raw_text, stored_option)

    return mention if mention.status != "UNCERTAIN" else whole
