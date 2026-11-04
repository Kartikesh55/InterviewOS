from uuid import UUID

from pydantic import Field, field_validator

from app.models.interview import QuestionSource
from app.schemas.common import ApiSchema


class QuestionGenerationRequest(ApiSchema):
    target_role: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    number_of_questions: int = Field(ge=1, le=20)

    @field_validator("target_role", "difficulty")
    @classmethod
    def validate_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("targetRole and difficulty must not be blank")
        return value.strip()


class GeneratedQuestion(ApiSchema):
    question_text: str = Field(min_length=1)
    evaluation_criteria: list[str] = Field(min_length=1)

    @field_validator("question_text")
    @classmethod
    def validate_question_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("questionText must not be blank")
        return value.strip()

    @field_validator("evaluation_criteria")
    @classmethod
    def validate_criteria(cls, values: list[str]) -> list[str]:
        normalized = [" ".join(value.split()).casefold() for value in values]
        if any(not value for value in normalized):
            raise ValueError("evaluation criteria must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("evaluation criteria must not contain duplicates")
        return [" ".join(value.split()) for value in values]


class QuestionGenerationResponse(ApiSchema):
    questions: list[GeneratedQuestion] = Field(min_length=1)


class InterviewQuestionResponse(ApiSchema):
    id: UUID
    question_text: str
    question_order: int
    source: QuestionSource
    evaluation_criteria: list[str]
