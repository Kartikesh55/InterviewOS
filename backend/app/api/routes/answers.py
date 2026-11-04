from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.schemas.answer import InterviewAnswerResponse, SubmitAnswerRequest
from app.schemas.interview import InterviewReportResponse
from app.services import answer_service


router = APIRouter(prefix="/api/interviews", tags=["answers"])
DbSession = Annotated[Session, Depends(get_db_session)]


@router.post(
    "/{interview_id}/questions/{question_id}/answers",
    response_model=InterviewAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_answer(
    interview_id: UUID,
    question_id: UUID,
    request: SubmitAnswerRequest,
    session: DbSession,
):
    return answer_service.submit_answer(
        session,
        interview_id,
        question_id,
        request.candidate_answer,
    )


@router.get("/{interview_id}/report", response_model=InterviewReportResponse)
def get_interview_report(interview_id: UUID, session: DbSession):
    return answer_service.get_interview_report(session, interview_id)
