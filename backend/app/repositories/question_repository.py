from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.interview import InterviewQuestion


def list_questions(session: Session, interview_id: UUID) -> list[InterviewQuestion]:
    statement = (
        select(InterviewQuestion)
        .where(InterviewQuestion.interview_id == interview_id)
        .options(selectinload(InterviewQuestion.criteria))
        .order_by(InterviewQuestion.question_order)
    )
    return list(session.scalars(statement).all())


def get_question(
    session: Session,
    interview_id: UUID,
    question_id: UUID,
    *,
    for_update: bool = False,
) -> InterviewQuestion | None:
    statement = (
        select(InterviewQuestion)
        .where(
            InterviewQuestion.id == question_id,
            InterviewQuestion.interview_id == interview_id,
        )
        .options(selectinload(InterviewQuestion.criteria))
    )
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def get_question_at_order(
    session: Session,
    interview_id: UUID,
    question_order: int,
    *,
    for_update: bool = False,
) -> InterviewQuestion | None:
    statement = (
        select(InterviewQuestion)
        .where(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.question_order == question_order,
        )
        .options(selectinload(InterviewQuestion.criteria))
    )
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)
