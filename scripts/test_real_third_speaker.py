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
        key="major_problems",
        text_hi=(
            "आपके हिसाब से इस समय "
            "सबसे बड़ी समस्या क्या है?"
        ),
        type="single_choice",
        options=[],
        selected_answer="Inflation",
    )


def make_options():
    return [
        CanonicalOption(
            value="Inflation",
            labels=[
                "Inflation",
                "महंगाई",
                "महँगाई",
            ],
        ),
        CanonicalOption(
            value="Unemployment",
            labels=[
                "Unemployment",
                "बेरोजगारी",
            ],
        ),
    ]


def make_policy():
    return AuditTagPolicy(
        tag="major_problems",
        placeholder="Major Problems",
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
                    id=7001,
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
                    id=8001,
                    text="Asked Right",
                    children=[],
                ),
                DispositionNode(
                    id=8002,
                    text="Mismatch",
                    children=[],
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
                    "ठीक है आपके हिसाब से "
                    "इस समय सबसे बड़ी समस्या क्या है"
                ),
            ),
            SpeechTurn(
                speaker="respondent",
                text="महंगाई",
            ),
            SpeechTurn(
                speaker="agent",
                text="महंगाई",
            ),
            SpeechTurn(
                speaker="unknown",
                text="कितने बच्चे",
            ),
        ]
    )

    result = audit_question(
        question=make_question(),
        dialogue=dialogue,
        canonical_options=make_options(),
        tag_policy=make_policy(),
    )

    print()
    print("=== REAL THIRD SPEAKER TEST ===")
    print()

    print(
        result.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    main()