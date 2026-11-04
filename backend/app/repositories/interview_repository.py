from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.interview import Interview, InterviewQuestion, InterviewStatus


def get_interview(
    session: Session,
    interview_id: UUID,
    *,
    for_update: bool = False,
    with_questions: bool = False,
) -> Interview | None:
    statement = select(Interview).where(Interview.id == interview_id)
    if with_questions:
        statement = statement.options(
            selectinload(Interview.questions).selectinload(InterviewQuestion.criteria)
        )
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def create_interview(session: Session, interview: Interview) -> Interview:
    session.add(interview)
    session.flush()
    return interview


def get_interview_status(session: Session, interview_id: UUID) -> InterviewStatus | None:
    return session.scalar(
        select(Interview.status).where(Interview.id == interview_id)
    )
