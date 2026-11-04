from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.models.interview import CriterionStatus, EvaluationStatus
from app.schemas.common import ApiSchema


class SubmitAnswerRequest(ApiSchema):
    candidate_answer: str = Field(min_length=1)

    @field_validator("candidate_answer")
    @classmethod
    def validate_nonblank_answer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("candidateAnswer must not be blank")
        return value


class CriterionAssessmentResponse(ApiSchema):
    criterion: str
    status: CriterionStatus
    evidence: str


class InterviewAnswerResponse(ApiSchema):
    id: UUID
    question_id: UUID
    candidate_answer: str
    submitted_at: datetime
    evaluation_status: EvaluationStatus
    technical_accuracy: float | None = None
    completeness: float | None = None
    clarity: float | None = None
    depth: float | None = None
    overall_score: float | None = None
    criterion_assessments: list[CriterionAssessmentResponse] = Field(
        default_factory=list
    )
    strengths: list[str] = Field(default_factory=list)
    missing_concepts: list[str] = Field(default_factory=list)
    feedback: str | None = None
    suggested_follow_up: str | None = None
    suggested_follow_up_criteria: list[str] = Field(default_factory=list)
