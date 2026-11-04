from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.interview import InterviewAnswer


def get_answer_for_question(
    session: Session,
    question_id: UUID,
    *,
    for_update: bool = False,
) -> InterviewAnswer | None:
    statement = (
        select(InterviewAnswer)
        .where(InterviewAnswer.interview_question_id == question_id)
        .options(
            selectinload(InterviewAnswer.assessments),
            selectinload(InterviewAnswer.strengths),
            selectinload(InterviewAnswer.missing_concepts),
            selectinload(InterviewAnswer.follow_up_criteria),
        )
    )
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def list_answers_for_question(
    session: Session,
    question_id: UUID,
) -> list[InterviewAnswer]:
    statement = (
        select(InterviewAnswer)
        .where(InterviewAnswer.interview_question_id == question_id)
        .options(
            selectinload(InterviewAnswer.assessments),
            selectinload(InterviewAnswer.strengths),
            selectinload(InterviewAnswer.missing_concepts),
            selectinload(InterviewAnswer.follow_up_criteria),
        )
        .order_by(InterviewAnswer.submitted_at)
    )
    return list(session.scalars(statement).all())
