from src.audit_engine.question_audit import audit_question
from src.audit_policy.models import (
    AuditTagPolicy,
    DispositionNode,
    ValidationPolicy,
)
from src.dialogue.models import (
    QuestionDialogue,
    SpeechTurn,
)
from src.domain.models import SurveyQuestion
from src.resolver.models import CanonicalOption


def make_question():
    return SurveyQuestion(
        key="state_govt_change",
        text_hi=(
            "क्या आप राज्य सरकार में बदलाव "
            "देखना चाहते हैं या नहीं?"
        ),
        type="single_choice",
        options=[],
        selected_answer="Yes",
    )


def make_options():
    return [
        CanonicalOption(
            value="Yes",
            labels=[
                "Yes",
                "हाँ",
                "हां",
            ],
        ),
        CanonicalOption(
            value="No",
            labels=[
                "No",
                "नहीं",
                "नही",
            ],
        ),
    ]


def make_policy():
    return AuditTagPolicy(
        tag="state_govt_change",
        placeholder="State Government Change",
        project_code="MANUAL-AUDIO-TEST",
        active=True,
        order=1,
        tag_type="console",
        question_tag_id=1,

        question_validation=ValidationPolicy(
            enabled=True,
            validation_type="single",
            dispositions=[
                DispositionNode(
                    id=2001,
                    text="Asked Right",
                    children=[],
                ),
            ],
        ),

        answer_validation=ValidationPolicy(
            enabled=True,
            validation_type="single",
            dispositions=[
                DispositionNode(
                    id=3000,
                    text=(
                        "Respondent answer "
                        "without Prompting"
                    ),
                    children=[
                        DispositionNode(
                            id=3001,
                            text=(
                                "Yes - "
                                "No Prompting Done"
                            ),
                            children=[],
                        ),
                    ],
                ),
                DispositionNode(
                    id=4000,
                    text=(
                        "Respondent answer "
                        "after Prompting"
                    ),
                    children=[
                        DispositionNode(
                            id=4001,
                            text=(
                                "Yes - "
                                "Prompting Done"
                            ),
                            children=[],
                        ),
                    ],
                ),
            ],
        ),
    )


def main():
    dialogue = QuestionDialogue(
        turns=[
            SpeechTurn(
                speaker="agent",
                text=(
                    "क्या आप राज्य सरकार में बदलाव "
                    "देखना चाहते हैं या नहीं"
                ),
            ),
            SpeechTurn(
                speaker="respondent",
                text="मुझे पता नहीं",
            ),
            SpeechTurn(
                speaker="agent",
                text="हाँ बोल दीजिए",
            ),
            SpeechTurn(
                speaker="respondent",
                text="हाँ",
            ),
        ]
    )

    result = audit_question(
        question=make_question(),
        dialogue=dialogue,
        canonical_options=make_options(),
        tag_policy=make_policy(),

        no_prompting_path=[
            "Respondent answer without Prompting",
            "Yes - No Prompting Done",
        ],

        prompting_path=[
            "Respondent answer after Prompting",
            "Yes - Prompting Done",
        ],
    )

    print()
    print("=== REAL AUDIO AUDIT TEST ===")
    print()

    print(
        result.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    main()