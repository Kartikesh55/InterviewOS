import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.graphs.question_graph import question_graph
from app.ai.services.question_service import QuestionGenerationError
from app.core.exceptions import (
    LifecycleConflict,
    QuestionGenerationFailed,
    ResourceNotFound,
)
from app.models.interview import (
    InterviewQuestion,
    InterviewStatus,
    QuestionCriterion,
    QuestionSource,
)
from app.repositories import interview_repository, question_repository
from app.schemas.question import (
    GeneratedQuestion,
    InterviewQuestionResponse,
)
from app.services.mapping import question_response


logger = logging.getLogger(__name__)


def generate_questions(
    session: Session,
    interview_id: UUID,
) -> list[InterviewQuestionResponse]:
    with session.begin():
        interview = interview_repository.get_interview(
            session,
            interview_id,
            for_update=True,
        )
        if interview is None:
            raise ResourceNotFound(f"Interview not found: {interview_id}")
        existing = question_repository.list_questions(session, interview_id)
        if existing:
            return [question_response(item) for item in existing]
        if interview.status != InterviewStatus.CREATED:
            raise LifecycleConflict(
                "Questions can only be generated for an interview in CREATED state"
            )
        role = interview.target_role
        difficulty = interview.difficulty.value
        question_limit = interview.number_of_questions

    try:
        result = question_graph.invoke(
            {
                "target_role": role,
                "difficulty": difficulty,
                "number_of_questions": question_limit,
                "questions": [],
            }
        )
        generated = [
            item if isinstance(item, GeneratedQuestion) else GeneratedQuestion.model_validate(item)
            for item in result["questions"]
        ]
    except (QuestionGenerationError, KeyError, TypeError, ValueError) as error:
        logger.exception("Question generation failed for interview %s", interview_id)
        raise QuestionGenerationFailed(str(error)) from error
    except Exception as error:
        logger.exception("Question generation failed for interview %s", interview_id)
        raise QuestionGenerationFailed("Question generation failed") from error

    if len(generated) != question_limit:
        raise QuestionGenerationFailed(
            "AI model returned an unexpected number of questions"
        )

    with session.begin():
        interview = interview_repository.get_interview(
            session,
            interview_id,
            for_update=True,
        )
        if interview is None:
            raise ResourceNotFound(f"Interview not found: {interview_id}")
        existing = question_repository.list_questions(session, interview_id)
        if existing:
            return [question_response(item) for item in existing]
        if interview.status != InterviewStatus.CREATED:
            raise LifecycleConflict(
                "Questions can only be generated for an interview in CREATED state"
            )

        questions = []
        for index, item in enumerate(generated, start=1):
            question = InterviewQuestion(
                question_text=item.question_text,
                question_order=index,
                source=QuestionSource.GENERATED,
                interview_id=interview_id,
                criteria=[
                    QuestionCriterion(criterion_order=order, criterion=criterion)
                    for order, criterion in enumerate(item.evaluation_criteria)
                ],
            )
            questions.append(question)
        session.add_all(questions)
        session.flush()
        return [question_response(item) for item in questions]


def get_current_question(
    session: Session,
    interview_id: UUID,
) -> InterviewQuestionResponse:
    interview = interview_repository.get_interview(session, interview_id)
    if interview is None:
        raise ResourceNotFound(f"Interview not found: {interview_id}")
    if interview.status != InterviewStatus.IN_PROGRESS:
        raise LifecycleConflict(
            "Current question is available only while the interview is IN_PROGRESS"
        )
    if interview.current_question_order is None:
        raise LifecycleConflict("The interview has no current question")
    question = question_repository.get_question_at_order(
        session,
        interview_id,
        interview.current_question_order,
    )
    if question is None:
        raise ResourceNotFound(f"Current question not found for interview: {interview_id}")
    return question_response(question)


def advance_to_next_question(
    session: Session,
    interview_id: UUID,
) -> InterviewQuestionResponse:
    with session.begin():
        interview = interview_repository.get_interview(
            session,
            interview_id,
            for_update=True,
        )
        if interview is None:
            raise ResourceNotFound(f"Interview not found: {interview_id}")
        if interview.status != InterviewStatus.IN_PROGRESS:
            raise LifecycleConflict("Only IN_PROGRESS interviews can advance")
        if interview.current_question_order is None:
            raise LifecycleConflict("The interview has no current question")
        if interview.current_question_order >= interview.number_of_questions:
            raise LifecycleConflict("There is no next question")
        next_question = question_repository.get_question_at_order(
            session,
            interview_id,
            interview.current_question_order + 1,
            for_update=True,
        )
        if next_question is None:
            raise LifecycleConflict("There is no next question")
        interview.current_question_order += 1
        session.flush()
        return question_response(next_question)
