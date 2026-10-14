"""A fictional interview that exercises every behaviour of the audit engine.

Names, parties, places and answers are invented. The interview is fed
through the real runner (src/full_sample/audit_runner.py), so the demo shows
what the engine actually decides, not a mock-up. tests/test_demo.py pins the
outcomes, so the demo cannot drift from the engine unnoticed.
"""

from src.audit_policy.models import AuditProjectPolicy, AuditTagPolicy, DispositionNode, ValidationPolicy

PROJECT = "DEMO-SYNTHETIC"
INTERVIEW_ID = "DEMO-0001"

PARTIES = [
    ("प्रगति मोर्चा", "Pragati Morcha", "PGM"),
    ("किसान जन पार्टी", "Kisan Jan Party", "KJP"),
    ("नव विकास दल", "Nav Vikas Dal", "NVD"),
]
MLA_CANDIDATES = [
    ("अरुण कुमार वर्मा", "Arun Kumar Verma", 0),
    ("सलमा बानो", "Salma Bano", 1),
    ("दिनेश यादव", "Dinesh Yadav", 2),
]
PAST_CANDIDATES = [("रमेश चंद्र", "Ramesh Chandra", 0), ("सुनीता देवी", "Sunita Devi", 1)]
CM_CANDIDATES = [("विजय प्रताप", "Vijay Pratap", 0), ("कमला सिंह", "Kamla Singh", 1)]

DNR = " DO NOT READ THE OPTIONS [Note:- ऑप्शंस को मत पढ़िए।]"


def _party_choices():
    return [{"option_text": f"{hi} [{en}] *{code}*", "hindi": hi, "english": en, "party": code}
            for hi, en, code in PARTIES]


def _candidate_choices(candidates, current=True):
    choices = []
    for index, (hi, en, party) in enumerate(candidates):
        p_hi, p_en, code = PARTIES[party]
        if current:
            choices.append({"option_text": f"{hi} [{p_hi}] <{en}> {{{p_en}}} *{code}*", "hindi": hi,
                            "english": en, "party": code, "candidate_id": f"C{index + 1}"})
        else:
            choices.append({"option_text": f"{hi} [{en}]", "hindi": hi, "english": en, "party": code})
    return choices


YES_NO = [{"option_text": "हाँ", "hindi": "हाँ", "english": "Yes"},
          {"option_text": "नहीं", "hindi": "नहीं", "english": "No"}]
SCALE = [{"option_text": t, "hindi": t, "english": e} for t, e in [
    ("पूरी तरह संतुष्ट", "Completely satisfied"), ("कुछ हद तक संतुष्ट", "Somewhat satisfied"),
    ("कुछ हद तक असंतुष्ट", "Somewhat dissatisfied"), ("पूरी तरह असंतुष्ट", "Completely dissatisfied")]]

# tag: (placeholder, script, choices, question validation on?, answer tree, stored answer)
QUESTIONS = {
    "introduction": ("Introduction", "नमस्कार, हम एक रिसर्च कंपनी से आए हैं। हम आगामी चुनाव को लेकर सर्वे कर रहे हैं। क्या मैं आपसे कुछ सवाल पूछ सकता हूँ?", YES_NO, False, "intro", ["हाँ"]),
    "ac_name": ("Assembly constituency", "विधानसभा चुने", [{"option_text": "12. रामपुर [Rampur]", "hindi": "12. रामपुर", "english": "Rampur"}], False, "mm", ["12. रामपुर [Rampur]"]),
    "gender": ("Gender", "रेस्पोंडेंट का लिंग भरें (Do Not Ask) [Note:- इस सवाल को न पूछें।]", [{"option_text": "महिला", "hindi": "महिला", "english": "Female"}, {"option_text": "पुरुष", "hindi": "पुरुष", "english": "Male"}], False, "mm", ["महिला"]),
    "age": ("Age", "आपकी उम्र क्या है? (18 से अधिक उम्र के मतदाताओं की ही आयु भरें)", None, False, "mm", "42"),
    "state_govt_change": ("State government change", "उत्तर प्रदेश में 2027 के विधानसभा चुनाव के बाद में क्या आप राज्य सरकार में बदलाव देखना चाहते हैं या नहीं?", YES_NO, True, "nested", ["हाँ"]),
    "state_govt_change_party": ("Preferred party for government", "2027 विधान सभा चुनाव के बाद आप किस पार्टी की सरकार देखना चाहते हैं?" + DNR, _party_choices(), True, "nested", ["प्रगति मोर्चा [Pragati Morcha] *PGM*"]),
    "mla_choice": ("MLA choice", "आप अपने विधानसभा क्षेत्र में विधायक के रूप में किसको देखना चाहते हैं ?" + DNR, _candidate_choices(MLA_CANDIDATES), True, "nested", ["सलमा बानो [किसान जन पार्टी] <Salma Bano> {Kisan Jan Party} *KJP*"]),
    "vs_past_candidate": ("2022 vote: candidate", "2022 में हुए विधायक और मुख्यमंत्री वाले चुनाव में आपने किस प्रत्याशी को वोट दिया था?" + DNR, _candidate_choices(PAST_CANDIDATES, current=False), True, "flat", ["रमेश चंद्र [Ramesh Chandra]"]),
    "vs_past_party": ("2022 vote: party", "2022 में हुए विधायक और मुख्यमंत्री वाले चुनाव में आपने किस पार्टी को वोट दिया था?" + DNR, _party_choices(), True, "flat", ["प्रगति मोर्चा [Pragati Morcha] *PGM*"]),
    "mla_awareness": ("Knows current MLA", "अब हम आपसे वर्तमान विधायक के बारे में कुछ सवाल पूछेंगे। क्या आप अपने वर्तमान विधायक <MLA Name> को जानते हैं?", YES_NO, False, "mm", ["हाँ"]),
    "mla_satisfaction": ("MLA satisfaction", "आप अपने वर्तमान विधायक <MLA Name> के कामकाज से कितना संतुष्ट या असंतुष्ट हैं? READ ALL THE OPTION [Note:- सभी ऑप्शंस को ध्यान से पढ़े]", SCALE, False, "mm", ["कुछ हद तक संतुष्ट"]),
    "cm_choice": ("Chief Minister choice", "अब हम आने वाले कुछ सवालों में मुख्यमंत्री पद के दावेदारों के बारे में बात करेंगे | यदि आज विधानसभा चुनाव होते हैं तो आप किसे मुख्यमंत्री के रूप में देखना चाहेंगे?" + DNR, _candidate_choices(CM_CANDIDATES), True, "nested", ["कमला सिंह [किसान जन पार्टी] <Kamla Singh> {Kisan Jan Party} *KJP*"]),
    "voting_intention_ls_party": ("Lok Sabha vote intention", "यदि आज की तारीख में लोक सभा चुनाव होते हैं तो आप कौनसी पार्टी को वोट देंगे?" + DNR, _party_choices(), True, "flat", ["प्रगति मोर्चा [Pragati Morcha] *PGM*"]),
}

# Questions in the questionnaire that the audit policy does not audit.
UNAUDITED = {
    "first_name": "आपका नाम क्या है ? (First Name)",
    "religion": "आप किस धर्म का पालन करते हैं?",
    "caste": "आप निम्न में से किस जाति के हैं?",
    "income": "आपके परिवार का मासिक आय क्या है?",
    "mp_satisfaction": "अब हम आपसे वर्तमान सांसद के बारे में सवाल पूछेंगे। आप अपने वर्तमान सांसद <MP Name> के कामकाज से कितना संतुष्ट या असंतुष्ट हैं?",
    "pm_satisfaction": "देश के वर्तमान प्रधानमंत्री के अभी तक के कामकाज से आप कितने संतुष्ट या असंतुष्ट हैं?",
}

# (start, end, speaker, text, overlaps_other_speaker)
A, R, U = "speaker_0", "speaker_1", "unattributed"
TURNS = [
    (1.2, 12.6, A, "नमस्ते दीदी हम एक रिसर्च कंपनी से आए हैं आने वाले चुनाव पर सर्वे कर रहे हैं क्या मैं आपसे कुछ सवाल पूछ सकती हूँ", False),
    (12.9, 13.8, R, "हाँ पूछिए", False),
    (15.2, 16.6, A, "आपका नाम क्या है", False),
    (17.0, 17.9, R, "सुनीता", False),
    (20.3, 22.6, A, "आपकी विधानसभा रामपुर है ना", False),
    (23.0, 23.6, R, "हाँ", False),
    (26.7, 28.0, A, "आपकी उम्र क्या है", False),
    (28.4, 29.6, R, "बयालीस साल", False),
    (31.5, 34.5, A, "आपका धर्म क्या है और जाति क्या है", False),
    (35.0, 36.2, U, "जी हिंदू", False),
    (37.0, 38.0, A, "ठीक है", False),
    (40.3, 46.8, A, "अच्छा दीदी उत्तर प्रदेश में दो हजार सत्ताईस के विधानसभा चुनाव के बाद आप राज्य सरकार में बदलाव देखना चाहती हैं कि नहीं", False),
    (47.2, 48.6, R, "हाँ बदलाव चाहिए", False),
    (52.8, 58.4, A, "दो हजार सत्ताईस विधान सभा चुनाव के बाद आप कौन सी पार्टी की सरकार देखना चाहती हैं", True),
    (57.9, 58.3, R, "हम्म", True),
    (59.0, 60.4, R, "प्रगति मोर्चा की", False),
    (63.8, 69.5, A, "आप अपने विधानसभा क्षेत्र में विधायक के रूप में किसको देखना चाहती हैं", False),
    (70.0, 70.8, R, "पता नहीं", False),
    (71.2, 75.6, A, "जैसे अरुण कुमार वर्मा हैं सलमा बानो हैं दिनेश यादव हैं", False),
    (76.0, 77.2, R, "सलमा बानो", False),
    (80.8, 86.6, A, "दो हजार बाईस में हुए विधायक और मुख्यमंत्री वाले चुनाव में आपने किस प्रत्याशी को वोट दिया था", False),
    (87.0, 88.6, A, "रमेश चंद्र जी को दिया था ना", False),
    (89.0, 89.6, R, "हाँ", False),
    (92.8, 98.0, A, "और दो हजार बाईस में विधायक मुख्यमंत्री चुनाव में किस प्रत्याशी को वोट दिया था", False),
    (98.5, 99.6, R, "प्रगति मोर्चा", False),
    (102.8, 107.0, A, "क्या आप अपने वर्तमान विधायक को जानते हैं", False),
    (107.4, 108.0, R, "हाँ", False),
    (110.8, 118.5, A, "आप अपने वर्तमान विधायक के कामकाज से कितना संतुष्ट या असंतुष्ट हैं पूरी तरह संतुष्ट कुछ हद तक संतुष्ट कुछ हद तक असंतुष्ट या पूरी तरह असंतुष्ट", False),
    (119.0, 120.4, U, "कुछ हद तक", False),
    (124.8, 130.2, A, "यदि आज विधानसभा चुनाव होते हैं तो आप मुख्यमंत्री किसको देखना चाहेंगी", False),
    (130.6, 131.4, R, "पता नहीं", False),
    (131.8, 133.4, A, "कमला सिंह बोल दीजिए", False),
    (133.8, 134.8, R, "हाँ कमला सिंह", False),
    (140.8, 142.4, A, "लोकसभा में किसको", False),
    (142.8, 143.8, R, "प्रगति मोर्चा", False),
    (150.5, 152.5, A, "धन्यवाद आपका समय देने के लिए", False),
]
DURATION_SEC = 154.0

# Screen-time windows from the survey app: (tag, start, end).
WINDOWS = [
    ("introduction", 1.0, 14.0), ("ac_name", 20.0, 25.0), ("gender", 25.5, 26.0), ("age", 26.5, 31.0),
    ("state_govt_change", 40.0, 52.0), ("state_govt_change_party", 52.5, 63.0), ("mla_choice", 63.5, 80.0),
    ("vs_past_candidate", 80.5, 92.0), ("vs_past_party", 92.5, 102.0), ("mla_awareness", 102.5, 110.0),
    ("mla_satisfaction", 110.5, 124.0), ("cm_choice", 124.5, 140.0), ("voting_intention_ls_party", 140.5, 150.0),
]

# What a human auditor recorded for this fictional interview.
HUMAN = {
    "introduction": (None, ["Yes - Perfect introduction"]),
    "ac_name": (None, ["Asked Right"]),
    "gender": (None, ["Asked Right"]),
    "age": (None, ["Asked Right"]),
    "state_govt_change": (["Asked Right"], ["Respondent answer without Prompting", "Yes - No Prompting Done"]),
    "state_govt_change_party": (["Asked Right"], ["Respondent answer without Prompting", "Respondent says PGM"]),
    "mla_choice": (["Asked Right"], ["Respondent answer after Prompting", "Prompting - KJP"]),
    "vs_past_candidate": (["Asked Like - Did you vote for this person {person's name}?"], ["Prompting -PGM"]),
    "vs_past_party": (["Partially Question Asked"], ["Yes - No Prompting Done"]),
    "mla_awareness": (None, ["Asked Right"]),
    "mla_satisfaction": (None, ["Asked Right"]),
    "cm_choice": (["Asked Right"], ["Respondent answer after Prompting", "Prompting - KJP"]),
    "voting_intention_ls_party": (["Partially Question Asked"], ["Yes - No Prompting Done"]),
}


def _node(counter, text, children=(), comments=False):
    counter[0] += 1
    return DispositionNode(id=counter[0], text=text, comments_required=comments, children=list(children))


def _trees(counter):
    codes = [code for _, _, code in PARTIES]
    question = [
        _node(counter, "Asked Right"),
        _node(counter, "Not Audible - Agent did not ask the question"),
        _node(counter, "Partially Question Asked"),
        _node(counter, "Asked Like - Did you vote for this person {person's name}?"),
        _node(counter, "Asked Like - Will you vote for this party {party name}?"),
    ]
    trees = {
        "mm": [_node(counter, "Asked Right"), _node(counter, "Mismatch", comments=True),
               _node(counter, "Not Audible - No response"), _node(counter, "Not Audible - Agent did not ask the question")],
        "intro": [_node(counter, "Yes - Perfect introduction"), _node(counter, "Incomplete Introduction"),
                  _node(counter, "Not Audible - Agent did not ask the question")],
        "flat": [_node(counter, "Yes - No Prompting Done"), _node(counter, "Mismatch", comments=True),
                 _node(counter, "Not Audible - No response")] + [_node(counter, f"Prompting -{c}") for c in codes],
        "nested": [
            _node(counter, "Not Audible - No response"),
            _node(counter, "Mismatch", comments=True),
            _node(counter, "Respondent answer without Prompting",
                  [_node(counter, "Yes - No Prompting Done")] + [_node(counter, f"Respondent says {c}") for c in codes]),
            _node(counter, "Respondent answer after Prompting", [_node(counter, f"Prompting - {c}") for c in codes]),
        ],
    }
    return question, trees


def build_inputs() -> dict:
    """Runner inputs (the same shapes a real sample folder provides)."""
    counter = [1000]
    tags = {}
    for order, (tag, (placeholder, _, _, qv, tree, _)) in enumerate(QUESTIONS.items(), start=1):
        question_tree, trees = _trees(counter)
        tags[tag] = AuditTagPolicy(
            tag=tag, placeholder=placeholder, project_code=PROJECT, active=True, order=order,
            tag_type="multi_level_dropdown", question_tag_id=order,
            question_validation=ValidationPolicy(enabled=qv, validation_type="mld", dispositions=question_tree if qv else []),
            answer_validation=ValidationPolicy(enabled=True, validation_type="mld", dispositions=trees[tree]),
        )
    policy = AuditProjectPolicy(project_code=PROJECT, project_name="Synthetic demo survey", tags=tags)

    questions = []
    for index, (tag, (_, script, choices, _, _, _)) in enumerate(QUESTIONS.items(), start=1):
        questions.append({
            "tag": tag, "question_index": index, "question_text": script,
            "question_type": "single_choice" if choices else "numeric",
            "resolution_ready": bool(choices), "choice_catalog_status": "STATIC" if choices else "NO_STATIC_CHOICES",
            "choices": choices or [], "do_not_read_options": "DO NOT READ" in script,
        })
    for tag, script in UNAUDITED.items():
        questions.append({"tag": tag, "question_index": len(questions) + 1, "question_text": script,
                          "question_type": "text", "resolution_ready": False,
                          "choice_catalog_status": "NO_STATIC_CHOICES", "choices": [], "do_not_read_options": False})

    windows = [{
        "tag": tag, "question_index": list(QUESTIONS).index(tag) + 1, "start_sec": start, "end_sec": end,
        "question_text": QUESTIONS[tag][1], "stored_response": QUESTIONS[tag][5], "overlap_review_required": False,
    } for tag, start, end in WINDOWS]

    roles = {A: {"role": "agent", "confidence": "STRONG"}, R: {"role": "respondent", "confidence": "STRONG"}}
    interview_turns = []
    for number, (start, end, speaker, text, overlap) in enumerate(TURNS, start=1):
        interview_turns.append({
            "turn_index": number, "interview_turn_index": number, "speaker_id": speaker,
            "role": roles.get(speaker, {}).get("role", "unknown"), "start_sec": start, "end_sec": end,
            "duration_sec": round(end - start, 3), "asr_status": "COMPLETE", "transcript": text,
            "raw_cross_speaker_overlap": overlap, "raw_cross_speaker_overlap_sec": 0.4 if overlap else 0.0,
            "cross_speaker_overlap": overlap, "undetected_by_diarization": speaker == U, "export_for_asr": True,
        })

    dialogues = []
    for tag, start, end in WINDOWS:
        rows = []
        for turn in interview_turns:
            s, e = max(turn["start_sec"], start - 1.5), min(turn["end_sec"], end + 1.5)
            if e <= s:
                continue
            core = turn["end_sec"] > start and turn["start_sec"] < end
            rows.append({**turn, "turn_index": len(rows) + 1,
                         "regions": ["core" if core else ("context_before" if turn["end_sec"] <= start else "context_after")],
                         "touches_core": core})
        dialogues.append({"tag": tag, "question_index": list(QUESTIONS).index(tag) + 1,
                          "question_text": QUESTIONS[tag][1], "turns": rows})

    human_audit = {}
    for tag, (question_path, answer_path) in HUMAN.items():
        entry = {}
        if question_path:
            entry["quesVal"] = {"selectedOptions": {str(i): t for i, t in enumerate(question_path)}}
        if answer_path:
            entry["ansVal"] = {"selectedOptions": {str(i): t for i, t in enumerate(answer_path)}}
        human_audit[tag] = entry

    return {
        "dialogues": dialogues, "windows": windows, "survey_definition": {"questions": questions},
        "policy": policy, "human_audit": human_audit, "interview_turns": interview_turns,
    }
