from src.domain.models import SurveyQuestion
from src.resolver.models import AnswerResolution, CanonicalOption
from src.resolver.respondent_answer import resolve_respondent_answer


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

    return resolve_respondent_answer(
        raw_text=transcript_text,
        options=canonical_options,
        stored_option=stored_option,
    )