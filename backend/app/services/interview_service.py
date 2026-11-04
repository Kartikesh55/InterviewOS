from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import LifecycleConflict, ResourceNotFound
from app.models.interview import Difficulty, Interview, InterviewStatus
from app.repositories import interview_repository, question_repository
from app.schemas.interview import (
    CreateInterviewRequest,
    InterviewDetailsResponse,
    InterviewResponse,
)
from app.services.mapping import interview_response, question_response


def create_interview(
    session: Session,
    request: CreateInterviewRequest,
) -> InterviewResponse:
    with session.begin():
        interview = interview_repository.create_interview(
            session,
            Interview(
                target_role=request.target_role.strip(),
                difficulty=request.difficulty,
                number_of_questions=request.number_of_questions,
                status=InterviewStatus.CREATED,
            ),
        )
        return interview_response(interview)


def get_interview_details(
    session: Session,
    interview_id: UUID,
) -> InterviewDetailsResponse:
    interview = interview_repository.get_interview(
        session,
        interview_id,
        with_questions=True,
    )
    if interview is None:
        raise ResourceNotFound(f"Interview not found: {interview_id}")
    return InterviewDetailsResponse(
        **interview_response(interview).model_dump(),
        current_question_order=interview.current_question_order,
        questions=[
            question_response(question)
            for question in interview.questions
        ],
    )


def start_interview(session: Session, interview_id: UUID) -> InterviewResponse:
    with session.begin():
        interview = interview_repository.get_interview(
            session,
            interview_id,
            for_update=True,
        )
        if interview is None:
            raise ResourceNotFound(f"Interview not found: {interview_id}")
        if interview.status != InterviewStatus.CREATED:
            raise LifecycleConflict("Only CREATED interviews can be started")
        if not question_repository.list_questions(session, interview_id):
            raise LifecycleConflict("Generate questions before starting the interview")
        interview.status = InterviewStatus.IN_PROGRESS
        interview.current_question_order = 1
        session.flush()
        return interview_response(interview)


def complete_interview(session: Session, interview_id: UUID) -> InterviewResponse:
    with session.begin():
        interview = interview_repository.get_interview(
            session,
            interview_id,
            for_update=True,
        )
        if interview is None:
            raise ResourceNotFound(f"Interview not found: {interview_id}")
        if interview.status != InterviewStatus.IN_PROGRESS:
            raise LifecycleConflict("Only IN_PROGRESS interviews can be completed")
        interview.status = InterviewStatus.COMPLETED
        session.flush()
        return interview_response(interview)
