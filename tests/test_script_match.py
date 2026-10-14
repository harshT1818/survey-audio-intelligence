from src.question_validation.script_match import (
    assess_asking,
    build_option_index,
    build_profiles,
    clean_script,
    number_words,
    options_mentioned,
)
from src.resolver.models import CanonicalOption

# A small synthetic questionnaire with the shapes that matter: a preamble,
# a year, a piped answer, a do-not-read note and two look-alike questions.
QUESTIONS = {
    "change": "उत्तर प्रदेश में 2027 के विधानसभा चुनाव के बाद में क्या आप राज्य सरकार में बदलाव देखना चाहते हैं या नहीं?",
    "past_candidate": "2022 में हुए विधायक और मुख्यमंत्री वाले चुनाव में आपने किस प्रत्याशी को वोट दिया था? DO NOT READ THE OPTIONS [Note:- ऑप्शंस को मत पढ़िए।]",
    "past_party": "2022 में हुए विधायक और मुख्यमंत्री वाले चुनाव में आपने किस पार्टी को वोट दिया था? DO NOT READ THE OPTIONS [Note:- ऑप्शंस को मत पढ़िए।]",
    "cm": "अब हम आने वाले कुछ सवालों में मुख्यमंत्री पद के दावेदारों के बारे में बात करेंगे | यदि आज विधानसभा चुनाव होते हैं तो आप किसे मुख्यमंत्री के रूप में देखना चाहेंगे? DO NOT READ THE OPTIONS",
    "second": "अगर आपके चुने हुए नेता $#mla-Hindi को अपनी पार्टी से टिकट नहीं मिलता, तो आप विधायक के रूप में किसको देखना चाहेंगे?",
    "age": "आपकी उम्र क्या है? (18 से अधिक उम्र के मतदाताओं की ही आयु भरें)",
    "mla_awareness": "क्या आप अपने वर्तमान विधायक <MLA Name> को जानते हैं?",
}
PROFILES = build_profiles(QUESTIONS, {"mla": "रमेश कुमार"})

OPTIONS = [
    CanonicalOption(value="रमेश कुमार [Party A] *PA*", labels=[], aliases=["रमेश कुमार", "Ramesh Kumar", "PA"]),
    CanonicalOption(value="सुरेश यादव [Party B] *PB*", labels=[], aliases=["सुरेश यादव", "Suresh Yadav", "PB"]),
    CanonicalOption(value="याद नहीं आ रहा [Can't Remember]", labels=[], aliases=["याद नहीं आ रहा", "Can't Remember"]),
]


def turn(index, role, start, text, overlap=False):
    return {"turn_index": index, "role": role, "start_sec": start, "end_sec": start + 2,
            "asr_status": "COMPLETE", "transcript": text, "raw_cross_speaker_overlap": overlap}


def assess(tag, turns, **kwargs):
    return assess_asking(PROFILES[tag], turns, 10.0, 30.0, **kwargs)


def test_script_is_cleaned_to_its_spoken_form():
    assert number_words(2027) == "दो हजार सत्ताईस"
    spoken = clean_script(QUESTIONS["second"], {"mla": "रमेश कुमार"})
    assert "रमेश कुमार" in spoken and "$#" not in spoken
    assert "DO NOT" not in clean_script(QUESTIONS["past_party"])
    assert "मतदाताओं" not in clean_script(QUESTIONS["age"])


def test_paraphrase_with_fillers_gender_and_spoken_year_is_asked_right():
    result = assess("change", [turn(1, "agent", 11, "अच्छा दीदी उत्तर प्रदेश में दो हज़ार सत्ताईस विधान सभा चुनाव के बाद आप राज्य सरकार में बदलाव देखना चाहती हैं कि नहीं")])
    assert result.status == "ASKED_RIGHT"
    assert result.prefill_only is False


def test_skipped_preamble_still_counts():
    result = assess("cm", [turn(1, "agent", 11, "यदि आज विधानसभा चुनाव होते हैं तो आप मुख्यमंत्री किसको देखना चाहेंगी")])
    assert result.status == "ASKED_RIGHT"


def test_question_split_across_turns_is_scored_as_one_asking():
    turns = [
        turn(1, "agent", 11, "दो हजार बाईस में हुए विधायक और मुख्यमंत्री वाले चुनाव में"),
        turn(2, "agent", 13, "आपने किस प्रत्याशी को वोट दिया था"),
    ]
    assert assess("past_candidate", turns).status == "ASKED_RIGHT"


def test_partial_asking_is_not_asked_right():
    result = assess("change", [turn(1, "agent", 11, "दो हजार सत्ताईस में चुनाव")])
    assert result.status == "UNCERTAIN"
    assert "content was heard" in result.reasons[0]


def test_look_alike_question_is_not_credited():
    # The candidate question asked inside the party question's window.
    result = assess("past_party", [turn(1, "agent", 11, "दो हजार बाईस में विधायक और मुख्यमंत्री चुनाव में आपने किस प्रत्याशी को वोट दिया था")])
    assert result.status == "UNCERTAIN"
    assert any("similar question" in reason for reason in result.reasons)


def test_one_named_option_blocks_asked_right():
    index = build_option_index(OPTIONS)
    turns = [
        turn(1, "agent", 11, "दो हजार बाईस में विधायक मुख्यमंत्री चुनाव में किस प्रत्याशी को वोट दिया था"),
        turn(2, "agent", 15, "सुरेश यादव जी को"),
    ]
    result = assess("past_candidate", turns, option_index=index, do_not_read_options=True)
    assert result.status == "UNCERTAIN"
    assert result.named_options == ["सुरेश यादव [Party B] *PB*"]


def test_reading_several_options_is_prefill_only():
    index = build_option_index(OPTIONS)
    turns = [turn(1, "agent", 11, "दो हजार बाईस में विधायक मुख्यमंत्री चुनाव में किस प्रत्याशी को वोट दिया था रमेश कुमार या सुरेश यादव")]
    result = assess("past_candidate", turns, option_index=index, do_not_read_options=True)
    assert result.status == "ASKED_RIGHT"
    assert result.prefill_only is True


def test_repeating_the_respondents_answer_is_not_naming_an_option():
    index = build_option_index(OPTIONS)
    turns = [
        turn(1, "agent", 11, "दो हजार बाईस में विधायक मुख्यमंत्री चुनाव में किस प्रत्याशी को वोट दिया था"),
        turn(2, "respondent", 15, "सुरेश यादव को"),
        turn(3, "agent", 17, "सुरेश यादव जी को ठीक है"),
    ]
    result = assess("past_candidate", turns, option_index=index, do_not_read_options=True)
    assert result.named_options == []
    assert result.status == "ASKED_RIGHT"


def test_non_party_options_are_never_names():
    index = build_option_index(OPTIONS)
    assert options_mentioned(index, "प्रत्याशी का नाम याद है कि नहीं") == []


def test_missing_question_word_and_overlap_are_prefill_only():
    no_wh = assess("cm", [turn(1, "agent", 11, "यदि आज विधानसभा चुनाव होते हैं तो आप मुख्यमंत्री के रूप में इसको देखना चाहेंगी")])
    assert no_wh.status == "ASKED_RIGHT" and no_wh.prefill_only

    overlapped = assess("age", [turn(1, "agent", 11, "आपकी उम्र क्या है", overlap=True)])
    assert overlapped.status == "ASKED_RIGHT" and overlapped.prefill_only


def test_no_interviewer_speech_is_reported():
    result = assess("age", [turn(1, "respondent", 11, "बयालीस साल")])
    assert result.status == "NO_INTERVIEWER_SPEECH"


def test_question_started_just_before_the_window_is_found():
    result = assess("age", [turn(1, "agent", 7.5, "आपकी उम्र क्या है")])
    assert result.status == "ASKED_RIGHT"
