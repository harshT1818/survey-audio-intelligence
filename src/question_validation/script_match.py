"""Paraphrase-tolerant matching of interviewer speech against the script.

Interviewers rarely read a question verbatim: they add fillers and forms of
address, inflect for the respondent's gender, say years as words, swap
synonyms, split a question across turns and repeat it when the respondent
does not follow. Whole-string similarity punishes all of that.

This module instead measures how much of the question's *content* was
said: script words are weighted by how distinctive they are within the
questionnaire, matched tolerantly (spelling, gender forms, split or joined
words, a small domain synonym list), and scored over whole interviewer
passages. It is plain string processing, so it adds no model or GPU cost.

Coverage alone cannot tell a correct question from a leading one, so the
caller also gets the signals that block "Asked Right": a missing question
word, missing words that distinguish this question from its nearest
neighbour, and options named by the interviewer.
"""

import math
import re
import unicodedata
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from src.resolver.respondent_answer import HINDI_NUMBERS, skeleton

# --------------------------------------------------------------------------
# Script cleaning
# --------------------------------------------------------------------------

_INSTRUCTION_TAIL = re.compile(
    r"(DO\s*NOT\s*READ|READ\s+ALL\s+THE\s+OPTION|NOTE\s*:-|Read\s+All\s+The\s+Options).*$",
    flags=re.IGNORECASE | re.DOTALL,
)
_BRACKETED = re.compile(r"\[[^\]]*\]|\([^)]*\)|<[^>]*>|\{[^}]*\}")
_QUOTED_PLACEHOLDER = re.compile(r'"[A-Za-z ]*Name[A-Za-z ]*"')
_PIPED = re.compile(r"\$#([A-Za-z0-9_]+)-([A-Za-z_]+)")
_DIGITS = re.compile(r"\d+")
_NON_WORD = re.compile(r"[^\w\sऀ-ॣ०-ॿ]")

_NUMBER_WORD = {}
for _word, _value in HINDI_NUMBERS.items():
    _NUMBER_WORD.setdefault(_value, _word)


def number_words(value: int) -> str:
    """Hindi words for 0-9999, as Vaani writes spoken numbers."""
    if value == 0:
        return "शून्य"
    parts = []
    thousands, rest = divmod(value, 1000)
    if thousands:
        parts += [_NUMBER_WORD[thousands], "हजार"]
    hundreds, rest = divmod(rest, 100)
    if hundreds:
        parts += [_NUMBER_WORD[hundreds], "सौ"]
    if rest:
        parts.append(_NUMBER_WORD[rest])
    return " ".join(parts)


def clean_script(question_text: str, piped_values: dict[str, str] | None = None) -> str:
    """Spoken form of a question: instructions removed, pipes filled, digits as words."""
    piped_values = piped_values or {}
    text = _INSTRUCTION_TAIL.sub(" ", question_text or "")

    def pipe(match: re.Match) -> str:
        tag, field_name = match.group(1), match.group(2).lower()
        return piped_values.get(tag, "") if field_name == "hindi" else ""

    text = _PIPED.sub(pipe, text)
    text = _BRACKETED.sub(" ", text)
    text = _QUOTED_PLACEHOLDER.sub(" ", text)
    text = _DIGITS.sub(lambda m: f" {number_words(int(m.group()))} ", text)
    return " ".join(text.split())


# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------

WH = "<wh>"

# Interrogatives that make a question open ("which", "whom"). Interviewers
# swap them freely (किस पार्टी / कौन सी पार्टी), so they form one class.
WH_WORDS = {
    "किस", "किसको", "किसे", "किसकी", "किसका", "किसके", "किन", "किनको", "किन्हें",
    "कौन", "कौनसी", "कौनसा", "कौनसे",
}

# Function words, fillers and forms of address carry no question content.
STOPWORDS = {
    "में", "के", "की", "का", "को", "से", "है", "हैं", "था", "थी", "थे", "और", "या", "तो",
    "ही", "भी", "ने", "पर", "हम", "आप", "आपके", "आपकी", "आपका", "आपको", "आपने", "आपसे",
    "अपने", "अपनी", "अपना", "यह", "वह", "ये", "वो", "जो", "कि", "एक", "कुछ", "लिए",
    "हो", "होते", "होता", "होती", "हुए", "हुई", "हुआ", "रहे", "रहा", "रही", "जी", "अब",
    "क्या", "न", "सी", "सा", "तक", "यदि", "अगर", "तब", "जब", "वाले", "वाली", "वाला",
    "अच्छा", "ठीक", "दीदी", "भैया", "भाई", "सर", "मैडम", "प्लीज", "बताइए", "बताइये",
    "बोलिए", "बोलिये", "मतलब", "जैसे", "हाँ", "हां", "हम्म", "कृपया", "सकते", "सकती",
}

# Survey vernacular: words an interviewer may use for the same thing.
SYNONYMS = {
    "एमएलए": "विधायक", "विधायकी": "विधायक", "एमपी": "सांसद", "सीएम": "मुख्यमंत्री",
    "पीएम": "प्रधानमंत्री", "कैंडिडेट": "प्रत्याशी", "उम्मीदवार": "प्रत्याशी",
    "उम्मीदवारों": "प्रत्याशी", "इलेक्शन": "चुनाव", "दल": "पार्टी", "परिवर्तन": "बदलाव",
    "मतदान": "वोट", "समर्थन": "वोट",
}

# Systematic Vaani confusions observed in these interviews: "को वोट" is
# often heard as one word.
ASR_VARIANTS = {"कोर्ट": ["को", "वोट"], "कोड": ["को", "वोट"], "वोड": ["वोट"]}


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = text.replace("़", "").replace("ँ", "ं")  # nukta, chandrabindu
    text = _NON_WORD.sub(" ", text)
    return " ".join(text.split())


# Words the script writes as one token but speech or ASR splits (or the
# reverse). Joined before matching so both sides agree.
COMPOUNDS = {"विधानसभा", "लोकसभा", "कौनसी", "कौनसा", "कौनसे", "मुख्यमंत्री", "प्रधानमंत्री"}

# Inflections stripped so gender, number and tense forms of the same verb
# or noun match (चाहते / चाहती / चाहेंगे / चाहिए). Longest first.
_SUFFIXES = sorted([
    "ेंगे", "ेंगी", "ेगा", "ेगी", "ोगे", "ोगी", "ियों", "ियां", "ाओं", "ाएं",
    "ते", "ती", "ता", "ने", "ना", "नी", "ें", "ों", "ीं", "िए", "िये",
    "ए", "े", "ी", "ा", "ो",
], key=len, reverse=True)


def stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _words(text: str) -> list[str]:
    words = normalize_text(text).split()
    joined, i = [], 0
    while i < len(words):
        if i + 1 < len(words) and words[i] + words[i + 1] in COMPOUNDS:
            joined.append(words[i] + words[i + 1])
            i += 2
        else:
            joined.append(words[i])
            i += 1
    return joined


def tokens(text: str, keep_stopwords: bool = True) -> list[str]:
    """Matching units: synonyms mapped, question words unified, stemmed."""
    out = []
    for word in _words(text):
        for part in ASR_VARIANTS.get(word, [word]):
            part = SYNONYMS.get(part, part)
            if part in WH_WORDS:
                out.append(WH)
            elif keep_stopwords or part not in STOPWORDS:
                out.append(part if part in STOPWORDS else stem(part))
    return out


def content_tokens(text: str) -> list[str]:
    return [t for t in tokens(text, keep_stopwords=False)]


def _token_present(token: str, spoken: list[str]) -> bool:
    if token in spoken:
        return True
    if token == WH:
        return False
    skel = skeleton(token)
    joined = [a + b for a, b in zip(spoken, spoken[1:])]
    for candidate in spoken + joined:
        if len(skel) >= 3 and skeleton(candidate) == skel:
            return True
        if len(token) >= 5 and fuzz.ratio(token, candidate) >= 85:
            return True
        if len(token) >= 4 and len(candidate) > len(token) and token in candidate:
            return True
    return False


# --------------------------------------------------------------------------
# Question profiles
# --------------------------------------------------------------------------

WH_WEIGHT = 1.5

# Introductory sentences ("अब हम आपसे ... कुछ सवाल पूछेंगे") are often
# skipped without the question counting as wrongly asked.
PREAMBLE_FACTOR = 0.1

# Names piped in from earlier answers are often garbled by ASR.
PIPED_NAME_FACTOR = 0.5

LOOK_ALIKE_OVERLAP = 0.6

_SENTENCE_END = re.compile(r"[।|?॥]")


def core_sentence(spoken_script: str) -> str:
    """The sentence that carries the question: the last one with a question word."""
    sentences = [s for s in _SENTENCE_END.split(spoken_script) if s.strip()]
    if not sentences:
        return spoken_script
    for sentence in reversed(sentences):
        words = set(tokens(sentence))
        if WH in words or "क्या" in words:
            return sentence
    return sentences[-1]


@dataclass
class ScriptProfile:
    tag: str
    spoken_script: str
    weights: dict[str, float]
    distinctive: set[str] = field(default_factory=set)
    has_wh: bool = False
    # (look-alike profile, words only this question has, words only it has)
    look_alikes: list[tuple["ScriptProfile", set[str], set[str]]] = field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(self.weights.values())


def build_profiles(
    questions: dict[str, str],
    piped_values: dict[str, str] | None = None,
) -> dict[str, ScriptProfile]:
    """Profiles for every question in a questionnaire, keyed by tag.

    Weights are inverse document frequency across the questionnaire, so a
    word that appears in most questions ("चुनाव") counts for little and a
    word that marks this question ("सांसद", "बदलाव") counts for a lot.
    """
    spoken = {tag: clean_script(text, piped_values) for tag, text in questions.items()}
    token_sets = {tag: set(content_tokens(text)) for tag, text in spoken.items()}
    core_sets = {tag: set(content_tokens(core_sentence(text))) for tag, text in spoken.items()}
    piped_words = {
        word for value in (piped_values or {}).values() for word in content_tokens(value)
    }
    count = max(len(token_sets), 1)
    document_frequency: dict[str, int] = {}
    for token_set in token_sets.values():
        for token in token_set:
            document_frequency[token] = document_frequency.get(token, 0) + 1

    profiles = {}
    for tag, token_set in token_sets.items():
        weights = {}
        for token in token_set:
            if token == WH:
                weights[token] = WH_WEIGHT
            else:
                weight = math.log((count + 1) / (document_frequency[token] + 0.5))
                if token not in core_sets[tag]:
                    weight *= PREAMBLE_FACTOR
                if token in piped_words:
                    weight *= PIPED_NAME_FACTOR
                weights[token] = round(weight, 4)
        profiles[tag] = ScriptProfile(tag=tag, spoken_script=spoken[tag], weights=weights, has_wh=WH in token_set)

    # Words that separate each question from its most similar neighbour.
    # A neighbour containing all of this question's words (a longer
    # variant) cannot be told apart from this side, so it is skipped.
    for tag, profile in profiles.items():
        own = token_sets[tag] - {WH}
        best_tag, best_overlap = None, 0.0
        for other, other_set in token_sets.items():
            if other == tag or not own or own <= other_set:
                continue
            shared = sum(profile.weights.get(t, 0) for t in own & other_set)
            overlap = shared / max(sum(profile.weights[t] for t in own), 1e-9)
            if overlap > best_overlap:
                best_tag, best_overlap = other, overlap
        if best_tag is not None:
            profile.distinctive = own - token_sets[best_tag]

    # Look-alikes: other questions sharing most of this one's weighted
    # content (vs_past_candidate / vs_past_party). A passage only counts
    # for this question if it fits it at least as well as each look-alike.
    for tag, profile in profiles.items():
        own_total = sum(w for t, w in profile.weights.items() if t != WH) or 1.0
        for other, other_profile in profiles.items():
            if other == tag or token_sets[other] == token_sets[tag]:
                continue
            shared = sum(w for t, w in profile.weights.items() if t != WH and t in token_sets[other])
            if shared / own_total >= LOOK_ALIKE_OVERLAP:
                profile.look_alikes.append((
                    other_profile,
                    token_sets[tag] - token_sets[other] - {WH},
                    token_sets[other] - token_sets[tag] - {WH},
                ))
    return profiles


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

@dataclass
class ScriptMatch:
    coverage: float
    distinctive_coverage: float | None
    has_wh: bool
    matched: list[str]
    missing: list[str]


def score_speech(profile: ScriptProfile, text: str) -> ScriptMatch:
    spoken = tokens(text)
    matched, missing = [], []
    for token, weight in sorted(profile.weights.items(), key=lambda item: -item[1]):
        (matched if _token_present(token, spoken) else missing).append(token)
    total = profile.total or 1.0
    coverage = sum(profile.weights[t] for t in matched) / total

    distinctive_coverage = None
    if profile.distinctive:
        distinctive_total = sum(profile.weights[t] for t in profile.distinctive) or 1.0
        distinctive_coverage = sum(
            profile.weights[t] for t in profile.distinctive if t in matched
        ) / distinctive_total

    return ScriptMatch(
        coverage=round(coverage, 4),
        distinctive_coverage=None if distinctive_coverage is None else round(distinctive_coverage, 4),
        has_wh=WH in spoken,
        matched=matched,
        missing=missing,
    )


# --------------------------------------------------------------------------
# Options named by the interviewer
# --------------------------------------------------------------------------

@dataclass
class OptionIndex:
    """Spoken forms of party and candidate options, for spotting names read aloud."""
    aliases: dict[str, set[str]]
    names: dict[str, set[str]]
    unique: dict[str, set[str]]


_PARTY_CODE = re.compile(r"^[A-Z][A-Z()+.\- ]{1,15}$")


def build_option_index(options: list) -> OptionIndex:
    """Index party and candidate options by aliases and name words.

    Only options carrying a party code (BJP, SP, INC...) are indexed:
    "can't remember", "others" or NOTA are not names an interviewer could
    lead with. Name words shared by several options (सिंह, पार्टी) are kept,
    but naming an option also needs a word unique to it.
    """
    aliases, names, counts = {}, {}, {}
    for option in options:
        option_aliases = list(getattr(option, "aliases", []) or [])
        if not any(_PARTY_CODE.match(alias.strip()) for alias in option_aliases):
            continue
        alias_set = set()
        for alias in option_aliases:
            words = tokens(alias)
            if len(words) == 1 and words[0] not in STOPWORDS and len(words[0]) >= 3:
                alias_set.add(words[0])
        aliases[option.value] = alias_set
        label = option_aliases[0] if option_aliases else option.value
        name_words = {w for w in content_tokens(label) if len(w) >= 3 and w != WH}
        names[option.value] = name_words
        for word in name_words:
            counts[word] = counts.get(word, 0) + 1
    unique = {value: {w for w in words if counts[w] == 1} for value, words in names.items()}
    return OptionIndex(aliases=aliases, names=names, unique=unique)


def options_mentioned(index: OptionIndex, text: str) -> set[str]:
    spoken = tokens(text)
    found = set()
    for value, words in index.names.items():
        if any(alias in spoken for alias in index.aliases.get(value, ())):
            found.add(value)
            continue
        # A full name: two of its words, at least one unique to this option.
        heard = {w for w in words if _token_present(w, spoken)}
        if len(heard) >= 2 and heard & index.unique[value]:
            found.add(value)
    return found


# --------------------------------------------------------------------------
# Was the question asked?
# --------------------------------------------------------------------------

ASKED_RIGHT_COVERAGE = 0.70
PRE_WINDOW_SEC = 5.0


@dataclass
class AskingAssessment:
    status: str  # ASKED_RIGHT, UNCERTAIN or NO_INTERVIEWER_SPEECH
    coverage: float | None
    prefill_only: bool
    reasons: list[str]
    text: str = ""
    turn_indices: list = field(default_factory=list)
    named_options: list[str] = field(default_factory=list)


def interviewer_passages(turns: list[dict], start: float, end: float) -> list[list[dict]]:
    """Runs of interviewer turns, split where someone else says something.

    A run is scored as one asking, so a question split across turns or
    restated straight away counts as a whole.
    """
    inside = sorted(
        (
            t for t in turns
            if t.get("start_sec") is not None
            and start <= float(t["start_sec"]) <= end
            and t.get("asr_status") == "COMPLETE"
            and str(t.get("transcript") or "").strip()
        ),
        key=lambda t: float(t["start_sec"]),
    )
    runs, current = [], []
    for turn in inside:
        if turn.get("role") == "agent":
            current.append(turn)
        elif current and len(tokens(turn["transcript"])) >= 2:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def assess_asking(
    profile: ScriptProfile,
    turns: list[dict],
    window_start: float,
    window_end: float,
    option_index: OptionIndex | None = None,
    do_not_read_options: bool = False,
    threshold: float = ASKED_RIGHT_COVERAGE,
) -> AskingAssessment:
    """Judge whether the interviewer asked this question, from rich turns.

    Every interviewer passage near the window is scored; the best one that
    also contains this question's distinguishing words is used, so a later
    restatement can still count. "Asked Right" needs enough of the
    question's content. It is limited to prefill when the question word
    was not heard or several options were read out, and withheld when the
    interviewer named a single option on a do-not-read question.
    """
    start, end = window_start - PRE_WINDOW_SEC, window_end + 0.5
    runs = interviewer_passages(turns, start, end)
    if not runs:
        return AskingAssessment("NO_INTERVIEWER_SPEECH", None, False, ["No interviewer speech near the question."])

    def share(weights: dict[str, float], words: set[str], spoken: list[str]) -> float:
        total = sum(weights[w] for w in words)
        return sum(weights[w] for w in words if _token_present(w, spoken)) / total if total else 0.0

    def fits_best(match: ScriptMatch, passage: str) -> bool:
        # Compare only the words that differ: this question's own words
        # must be heard at least as much as the look-alike's own words.
        spoken = tokens(passage)
        return all(
            share(profile.weights, own_only, spoken) >= share(other.weights, other_only, spoken)
            for other, own_only, other_only in profile.look_alikes
        )

    scored = []
    for run in runs:
        passage = " ".join(t["transcript"] for t in run)
        match = score_speech(profile, passage)
        scored.append((match, run, fits_best(match, passage)))
    eligible = [item for item in scored if item[2]] or scored
    match, run, fits = max(eligible, key=lambda item: item[0].coverage)
    text = " ".join(t["transcript"] for t in run)

    reasons, prefill_only = [], False
    named = []
    if option_index is not None and do_not_read_options:
        in_script = options_mentioned(option_index, profile.spoken_script)
        heard_from_others: set[str] = set()
        window_turns = sorted(
            (t for t in turns if t.get("start_sec") is not None and start <= float(t["start_sec"]) <= end
             and str(t.get("transcript") or "").strip()),
            key=lambda t: float(t["start_sec"]),
        )
        for turn in window_turns:
            mentioned = options_mentioned(option_index, turn["transcript"]) - in_script
            if turn.get("role") == "agent":
                named += [m for m in mentioned if m not in heard_from_others and m not in named]
            else:
                heard_from_others |= mentioned

    if match.coverage < threshold:
        reasons.append(f"Only {match.coverage:.0%} of the question's content was heard.")
    if not fits:
        reasons.append("The interviewer's words fit a similar question better than this one.")
    if len(named) == 1:
        reasons.append("The interviewer named one answer option on a do-not-read question.")

    if reasons:
        status = "UNCERTAIN"
    else:
        status = "ASKED_RIGHT"
        if profile.has_wh and not match.has_wh:
            prefill_only = True
            reasons.append("The question word (which/whom) was not heard.")
        if len(named) >= 2:
            prefill_only = True
            reasons.append("The interviewer read out answer options; prompting is judged on the answer side.")
        if any(t.get("raw_cross_speaker_overlap") for t in run):
            prefill_only = True
            reasons.append("Another voice overlaps the question; listen to confirm.")

    return AskingAssessment(
        status=status,
        coverage=match.coverage,
        prefill_only=prefill_only,
        reasons=reasons,
        text=text,
        turn_indices=[t.get("turn_index") for t in run],
        named_options=named,
    )


def to_validation_result(assessment: AskingAssessment, expected_question: str):
    """QuestionValidationResult for the audit engine; prefill-only becomes review_required."""
    from src.question_validation.models import QuestionValidationResult

    status = "ASKED_RIGHT" if assessment.status == "ASKED_RIGHT" else "UNCERTAIN"
    if status == "ASKED_RIGHT" and not assessment.prefill_only:
        reason = "Interviewer speech covers the question's content."
    else:
        reason = " ".join(assessment.reasons) or "Question evidence was not strong enough."
    return QuestionValidationResult(
        expected_question=expected_question,
        transcript_text=assessment.text,
        status=status,
        confidence=min(1.0, max(0.0, assessment.coverage or 0.0)),
        matched_text=assessment.text or None,
        review_required=status != "ASKED_RIGHT" or assessment.prefill_only,
        reason=reason,
    )
