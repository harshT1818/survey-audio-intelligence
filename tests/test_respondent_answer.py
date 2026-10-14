from src.evidence_quality.gate import evaluate_answer_evidence
from src.full_sample.survey_options import choice_to_canonical_option
from src.resolver.models import CanonicalOption
from src.resolver.respondent_answer import (
    RULE_CONFIDENCE,
    resolve_respondent_answer,
    skeleton,
    spoken_numbers,
)


# Synthetic candidates: two share the surname "अखलाक", two share the
# honorific "हाजी".
CANDIDATES = [
    CanonicalOption(value="हाजी रशीद अखलाक [दल क]", aliases=["हाजी रशीद अखलाक"]),
    CanonicalOption(value="मो. शाहिद अखलाक [निर्दलीय]", aliases=["मो. शाहिद अखलाक"]),
    CanonicalOption(value="हाजी सलीम अंसारी [दल ख]", aliases=["हाजी सलीम अंसारी"]),
]

PARTIES = [
    CanonicalOption(value="Party A", aliases=["बसपा"]),
    CanonicalOption(value="Party B", aliases=["भाजपा"]),
]


def test_skeleton_merges_spelling_variants():
    assert skeleton("राशिद") == skeleton("रशीद")


def test_unique_partial_name_resolves_as_prefill_strength():
    result = resolve_respondent_answer("राशिद", CANDIDATES, "हाजी रशीद अखलाक [दल क]")

    assert result.status == "MATCH"
    assert result.resolved_option == "हाजी रशीद अखलाक [दल क]"
    assert result.confidence == RULE_CONFIDENCE


def test_shared_surname_alone_stays_uncertain():
    result = resolve_respondent_answer("अखलाक", CANDIDATES)

    assert result.status == "UNCERTAIN"


def test_honorific_alone_stays_uncertain():
    assert resolve_respondent_answer("हाजी जी", CANDIDATES).status == "UNCERTAIN"


def test_two_candidates_mentioned_stays_uncertain():
    assert resolve_respondent_answer("रशीद और सलीम", CANDIDATES).status == "UNCERTAIN"


def test_negation_blocks_mention():
    assert resolve_respondent_answer("रशीद नहीं चाहिए", CANDIDATES).status == "UNCERTAIN"


def test_offered_alternatives_block_mention():
    result = resolve_respondent_answer("या तो बसपा हो या कोई और", PARTIES)

    assert result.status == "UNCERTAIN"


def test_party_mention_inside_statement_and_asr_split():
    for text in ("बसपा आनी चाहिए", "बस पा रही थी"):
        result = resolve_respondent_answer(text, PARTIES, "Party A")
        assert result.status == "MATCH", text
        assert result.resolved_option == "Party A"


def test_spoken_number_matches_small_stored_value():
    assert spoken_numbers("मेरी पचपन साल") == [55]

    match = resolve_respondent_answer("मेरी पचपन", [], "55")

    assert match.status == "MATCH"


def test_spoken_number_never_contradicts_recorded_value():
    # अट्ठाईस (28) is easily misheard for अड़तीस (38).
    heard = resolve_respondent_answer("अट्ठाईस साल", [], "38")

    assert heard.status == "UNCERTAIN"
    assert heard.resolved_option is None


def test_numbers_are_never_compared_with_identifiers():
    assert resolve_respondent_answer("चौरासी", [], "9000000084").status == "UNCERTAIN"


def test_several_numbers_stay_uncertain():
    assert resolve_respondent_answer("पचपन या छप्पन", [], "55").status == "UNCERTAIN"
    assert resolve_respondent_answer("दस सत्तावन", [], "57").status == "UNCERTAIN"


def test_rule_based_answer_is_only_a_prefill_candidate():
    result = evaluate_answer_evidence("बसपा आनी चाहिए", PARTIES, "Party A")

    assert result.evidence_status == "MODERATE"
    assert result.automation_status == "PREFILL_CANDIDATE"
    assert result.review_required is True


def test_party_choices_get_spoken_aliases_but_person_choices_do_not():
    party = choice_to_canonical_option(
        {"option_text": "बहुजन समाज पार्टी [Bahujan Samaj Party] *BSP*", "party": "BSP"}
    )
    candidate = choice_to_canonical_option(
        {"option_text": "व्यक्ति क [बहुजन समाज पार्टी] *BSP*", "party": "BSP", "candidate_id": "7"}
    )
    # Past-vote catalogs list "Person [Party]" without a candidate ID.
    person_without_id = choice_to_canonical_option(
        {"option_text": "व्यक्ति ख [बहुजन समाज पार्टी] *BSP*", "party": "BSP"}
    )

    assert "बसपा" in party.aliases
    assert "बसपा" not in candidate.aliases
    assert "बसपा" not in person_without_id.aliases


def test_party_mention_does_not_resolve_a_person_choice():
    options = [
        choice_to_canonical_option(
            {"option_text": "व्यक्ति ख [बहुजन समाज पार्टी] *BSP*", "party": "BSP"}
        ),
        choice_to_canonical_option(
            {"option_text": "याद नहीं आ रहा [Can't Remember]"}
        ),
    ]

    result = resolve_respondent_answer("बसपा को", options, "याद नहीं आ रहा [Can't Remember]")

    assert result.status == "UNCERTAIN"
