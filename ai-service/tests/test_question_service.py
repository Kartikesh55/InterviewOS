from typing import Any

import pytest
from pydantic import ValidationError

from app.models import (
    AnswerEvaluationResponse,
    GeneratedQuestion,
    QuestionGenerationResponse,
)
from app.services import question_service


class MockStructuredLLM:
    def __init__(self, result: Any = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.prompt = ""

    def invoke(self, prompt: str) -> Any:
        self.prompt = prompt
        if self.error is not None:
            raise self.error
        return self.result


def test_generates_structured_questions_with_criteria(monkeypatch: pytest.MonkeyPatch):
    mock_llm = MockStructuredLLM(
        result={
            "questions": [
                {
                    "questionText": "Explain database transactions.",
                    "evaluationCriteria": ["Atomicity", "Isolation"],
                },
                {
                    "questionText": "How do indexes affect writes?",
                    "evaluationCriteria": ["Lookup benefit", "Write overhead"],
                },
            ]
        }
    )
    monkeypatch.setattr(question_service, "structured_llm", mock_llm)

    questions = question_service.generate_questions("Backend Engineer", "Intermediate", 2)

    assert questions == [
        GeneratedQuestion(
            questionText="Explain database transactions.",
            evaluationCriteria=["Atomicity", "Isolation"],
        ),
        GeneratedQuestion(
            questionText="How do indexes affect writes?",
            evaluationCriteria=["Lookup benefit", "Write overhead"],
        ),
    ]
    assert "specific, independently assessable" in mock_llm.prompt


@pytest.mark.parametrize(
    "question",
    [
        {"questionText": "   ", "evaluationCriteria": ["A criterion"]},
        {"questionText": "A valid question?", "evaluationCriteria": []},
        {"questionText": "A valid question?", "evaluationCriteria": ["  "]},
        {
            "questionText": "A valid question?",
            "evaluationCriteria": ["Criterion", " criterion "],
        },
    ],
)
def test_invalid_question_or_criteria_are_rejected(question: dict[str, Any]):
    with pytest.raises(ValidationError):
        GeneratedQuestion.model_validate(question)


def test_malformed_structured_output_fails_explicitly(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    monkeypatch.setattr(
        question_service,
        "structured_llm",
        MockStructuredLLM(result={"questions": [{"questionText": "No criteria"}]}),
    )

    with pytest.raises(question_service.QuestionGenerationError):
        question_service.generate_questions("Backend Engineer", "Intermediate", 1)

    assert "Question generation failed" in caplog.text


def test_unexpected_number_of_questions_is_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        question_service,
        "structured_llm",
        MockStructuredLLM(
            result={
                "questions": [
                    {
                        "questionText": "One question?",
                        "evaluationCriteria": ["Criterion"],
                    }
                ]
            }
        ),
    )

    with pytest.raises(
        question_service.QuestionGenerationError,
        match="unexpected number",
    ):
        question_service.generate_questions("Backend Engineer", "Intermediate", 2)


def test_evaluation_response_includes_follow_up_criteria_and_status():
    response = AnswerEvaluationResponse.model_validate(
        {
            "evaluationStatus": "COMPLETED",
            "technicalAccuracy": 8,
            "completeness": 8,
            "clarity": 8,
            "depth": 8,
            "overallScore": 8,
            "criterionAssessments": [],
            "strengths": [],
            "missingConcepts": [],
            "feedback": "Good.",
            "suggestedFollowUp": "How does indexing affect writes?",
            "suggestedFollowUpCriteria": ["Write amplification"],
        }
    )

    assert response.evaluationStatus == "COMPLETED"
    assert response.suggestedFollowUp == "How does indexing affect writes?"
    assert response.suggestedFollowUpCriteria == ["Write amplification"]
