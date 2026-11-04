from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.models.interview import Difficulty, InterviewStatus
from app.schemas.common import ApiSchema
from app.schemas.answer import InterviewAnswerResponse
from app.schemas.question import InterviewQuestionResponse


class CreateInterviewRequest(ApiSchema):
    target_role: str = Field(min_length=1)
    difficulty: Difficulty
    number_of_questions: int = Field(ge=1, le=20)

    @field_validator("target_role")
    @classmethod
    def validate_target_role(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("targetRole must not be blank")
        return value.strip()


class InterviewResponse(ApiSchema):
    id: UUID
    target_role: str
    difficulty: Difficulty
    number_of_questions: int
    status: InterviewStatus
    created_at: datetime


class InterviewDetailsResponse(InterviewResponse):
    current_question_order: int | None
    questions: list[InterviewQuestionResponse]


class InterviewQuestionReportResponse(InterviewQuestionResponse):
    answers: list[InterviewAnswerResponse]


class InterviewReportResponse(InterviewDetailsResponse):
    questions: list[InterviewQuestionReportResponse]
