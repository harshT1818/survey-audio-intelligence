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
        key="ac_name",
        text_hi="क्या आपका विधानसभा क्षेत्र बदलापुर है?",
        type="single_choice",
        options=[],
        selected_answer="Badlapur",
    )


def make_options():
    return [
        CanonicalOption(
            value="Badlapur",
            labels=[
                "Badlapur",
                "बदलापुर",
            ],
        ),
        CanonicalOption(
            value="Bijnor",
            labels=[
                "Bijnor",
                "बिजनौर",
            ],
        ),
    ]


def make_policy():
    return AuditTagPolicy(
        tag="ac_name",
        placeholder="Assembly Constituency",
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
                    id=5001,
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
                    id=6001,
                    text="Asked Right",
                    children=[],
                ),
                DispositionNode(
                    id=6002,
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
                text="ठीक है आपका विधानसभा क्षेत्र बदलापुर है",
            ),
            SpeechTurn(
                speaker="respondent",
                text="नहीं बिजनौर",
            ),
            SpeechTurn(
                speaker="agent",
                text="बिजनौर",
            ),
            SpeechTurn(
                speaker="respondent",
                text="हाँ बिजनौर",
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
    print("=== REAL LOCATION MISMATCH TEST ===")
    print()

    print(
        result.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    main()