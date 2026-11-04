from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.schemas.question import InterviewQuestionResponse
from app.services import question_service


router = APIRouter(prefix="/api/interviews/{interview_id}", tags=["questions"])
DbSession = Annotated[Session, Depends(get_db_session)]


@router.post("/questions", response_model=list[InterviewQuestionResponse])
def generate_interview_questions(interview_id: UUID, session: DbSession):
    return question_service.generate_questions(session, interview_id)


@router.get("/current-question", response_model=InterviewQuestionResponse)
def get_current_question(interview_id: UUID, session: DbSession):
    return question_service.get_current_question(session, interview_id)


@router.post("/next-question", response_model=InterviewQuestionResponse)
def advance_to_next_question(interview_id: UUID, session: DbSession):
    return question_service.advance_to_next_question(session, interview_id)
