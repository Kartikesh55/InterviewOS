from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.schemas.interview import (
    CreateInterviewRequest,
    InterviewDetailsResponse,
    InterviewResponse,
)
from app.services import interview_service


router = APIRouter(prefix="/api/interviews", tags=["interviews"])
DbSession = Annotated[Session, Depends(get_db_session)]


@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def create_interview(request: CreateInterviewRequest, session: DbSession):
    return interview_service.create_interview(session, request)


@router.get("/{interview_id}", response_model=InterviewDetailsResponse)
def get_interview(interview_id: UUID, session: DbSession):
    return interview_service.get_interview_details(session, interview_id)


@router.post("/{interview_id}/start", response_model=InterviewResponse)
def start_interview(interview_id: UUID, session: DbSession):
    return interview_service.start_interview(session, interview_id)


@router.post("/{interview_id}/complete", response_model=InterviewResponse)
def complete_interview(interview_id: UUID, session: DbSession):
    return interview_service.complete_interview(session, interview_id)
