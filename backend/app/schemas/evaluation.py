from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CriterionAssessment(BaseModel):
    criterion: str
    status: Literal["COVERED", "PARTIALLY_COVERED", "MISSING"]
    evidence: str = ""


class CriterionAssessmentDraft(CriterionAssessment):
    rationale: str = Field(min_length=1)


class AnswerEvaluationDraft(BaseModel):
    technicalAccuracy: float = Field(ge=0, le=10)
    clarity: float = Field(ge=0, le=10)
    depth: float = Field(ge=0, le=10)
    criterionAssessments: list[CriterionAssessmentDraft]
    feedback: str
    suggestedFollowUp: str | None = None
    suggestedFollowUpCriteria: list[str] = Field(default_factory=list)

class AnswerEvaluationRequest(BaseModel):
    question: str = Field(min_length=1)
    candidateAnswer: str = Field(min_length=1)
    targetRole: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    evaluationCriteria: list[str] = Field(min_length=1)

    @field_validator("question", "targetRole", "difficulty")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question, targetRole, and difficulty must not be blank")
        return value.strip()

    @field_validator("candidateAnswer")
    @classmethod
    def validate_nonblank_answer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("candidateAnswer must not be blank")
        return value

    @field_validator("evaluationCriteria")
    @classmethod
    def validate_criteria(cls, values: list[str]) -> list[str]:
        normalized = [" ".join(value.split()).casefold() for value in values]
        if any(not value for value in normalized):
            raise ValueError("evaluation criteria must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("evaluation criteria must not contain duplicates")
        return values


class AnswerEvaluationResponse(BaseModel):
    evaluationStatus: Literal["COMPLETED", "FAILED"] = "COMPLETED"
    technicalAccuracy: float | None = Field(default=None, ge=0, le=10)
    completeness: float | None = Field(default=None, ge=0, le=10)
    clarity: float | None = Field(default=None, ge=0, le=10)
    depth: float | None = Field(default=None, ge=0, le=10)
    overallScore: float | None = Field(default=None, ge=0, le=10)
    criterionAssessments: list[CriterionAssessment] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    missingConcepts: list[str] = Field(default_factory=list)
    feedback: str
    suggestedFollowUp: str | None = None
    suggestedFollowUpCriteria: list[str] = Field(default_factory=list)
