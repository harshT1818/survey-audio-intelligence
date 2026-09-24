from src.domain.models import SurveyQuestion
from src.resolver.closed_set import resolve_closed_set_answer
from src.resolver.models import AnswerResolution, CanonicalOption


def resolve_question_answer(
    question: SurveyQuestion,
    transcript_text: str,
    canonical_options: list[CanonicalOption],
) -> AnswerResolution:

    stored_option = (
        str(question.selected_answer)
        if question.selected_answer is not None
        else None
    )

    return resolve_closed_set_answer(
        raw_text=transcript_text,
        options=canonical_options,
        stored_option=stored_option,
    )