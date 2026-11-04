from typing import Literal

from pydantic import BaseModel, Field, field_validator


class QuestionGenerationRequest(BaseModel):
    targetRole: str = Field(min_length=1)
    difficulty: str
    numberOfQuestions: int = Field(ge=1, le=20)


class QuestionGenerationResponse(BaseModel):
    questions: list[str]


class AnswerEvaluationRequest(BaseModel):
    question: str = Field(min_length=1)
    candidateAnswer: str = Field(min_length=1)
    targetRole: str = Field(min_length=1)
    difficulty: str
    evaluationCriteria: list[str] = Field(min_length=1)

    @field_validator("candidateAnswer")
    @classmethod
    def candidate_answer_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("candidateAnswer must not be blank")
        return value

    @field_validator("evaluationCriteria")
    @classmethod
    def criteria_must_be_nonempty_and_unique(cls, values: list[str]) -> list[str]:
        normalized_criteria = set()
        for criterion in values:
            normalized = " ".join(criterion.split()).casefold()
            if not normalized:
                raise ValueError("evaluation criteria must not be blank")
            if normalized in normalized_criteria:
                raise ValueError("evaluation criteria must not contain duplicates")
            normalized_criteria.add(normalized)
        return values


class CriterionAssessment(BaseModel):
    criterion: str
    status: Literal["COVERED", "PARTIALLY_COVERED", "MISSING"]
    evidence: str = ""


class CriterionAssessmentDraft(BaseModel):
    criterion: str
    status: Literal["COVERED", "PARTIALLY_COVERED", "MISSING"]
    evidence: str = ""
    rationale: str = Field(min_length=1)


class AnswerEvaluationDraft(BaseModel):
    technicalAccuracy: float = Field(ge=0, le=10)
    clarity: float = Field(ge=0, le=10)
    depth: float = Field(ge=0, le=10)

    criterionAssessments: list[CriterionAssessmentDraft]
    feedback: str
    suggestedFollowUp: str | None = None


class AnswerEvaluationResponse(BaseModel):
    technicalAccuracy: float = Field(ge=0, le=10)
    completeness: float = Field(ge=0, le=10)
    clarity: float = Field(ge=0, le=10)
    depth: float = Field(ge=0, le=10)

    overallScore: float = Field(ge=0, le=10)

    criterionAssessments: list[CriterionAssessment]
    strengths: list[str]
    missingConcepts: list[str]
    feedback: str
    suggestedFollowUp: str | None