from typing import Any

import pytest
from pydantic import ValidationError

from app.ai.services import answer_service, question_service
from app.schemas.evaluation import AnswerEvaluationDraft, AnswerEvaluationRequest


CRITERIA = ["Explain hashing", "Describe collisions", "Discuss complexity"]


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


class MockChatModel:
    def __init__(self, structured):
        self.structured = structured

    def with_structured_output(self, *_args, **_kwargs):
        return self.structured


def assessment(criterion, status, evidence="", rationale="Substantive rationale."):
    return {
        "criterion": criterion,
        "status": status,
        "evidence": evidence,
        "rationale": rationale,
    }


def draft(assessments, **changes):
    value = {
        "technicalAccuracy": 8,
        "clarity": 9,
        "depth": 7,
        "criterionAssessments": assessments,
        "feedback": "This model feedback is replaced by assessment-derived feedback.",
        "suggestedFollowUp": "How would you test the design?",
        "suggestedFollowUpCriteria": ["Test coverage"],
    }
    value.update(changes)
    return value


def run_evaluation(monkeypatch, response, candidate_answer, criteria=CRITERIA):
    structured = MockStructuredLLM(result=response)
    monkeypatch.setattr(
        answer_service,
        "get_chat_model",
        lambda: MockChatModel(structured),
    )
    result = answer_service.evaluate_answer(
        question="Explain a hash map.",
        candidate_answer=candidate_answer,
        target_role="Software Engineer",
        difficulty="INTERMEDIATE",
        evaluation_criteria=criteria,
    )
    return result, structured


def test_strong_evaluation_calculates_scores_and_uses_validated_strengths(monkeypatch):
    answer = (
        "A hash function maps keys to buckets. "
        "Separate chaining stores colliding keys in a list. "
        "Lookup is O(1) on average."
    )
    result, _ = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment("Explain hashing", "COVERED", "maps keys to buckets"),
                assessment("Describe collisions", "COVERED", "stores colliding keys"),
                assessment("Discuss complexity", "COVERED", "O(1) on average"),
            ]
        ),
        answer,
    )
    assert result.completeness == 10
    assert result.overallScore == 8.6
    assert result.strengths == CRITERIA
    assert result.missingConcepts == []


def test_partial_missing_and_fabricated_evidence_are_safe(monkeypatch):
    result, _ = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment("Explain hashing", "COVERED", "fabricated hash detail"),
                assessment("Describe collisions", "PARTIALLY_COVERED", "handles collisions"),
                assessment("Discuss complexity", "MISSING"),
            ]
        ),
        "The map handles COLLISIONS\nusing buckets.",
    )
    assert [item.status for item in result.criterionAssessments] == [
        "MISSING",
        "PARTIALLY_COVERED",
        "MISSING",
    ]
    assert result.completeness == 1.67
    assert result.strengths == []
    assert result.missingConcepts == ["Explain hashing", "Discuss complexity"]
    assert "partially addressed" in result.feedback


def test_invented_and_duplicate_criteria_cannot_replace_input_criteria(monkeypatch):
    criteria = ["Explain hashing", "Discuss complexity"]
    result, _ = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment("Explain hashing", "COVERED", "hash function"),
                assessment("Explain hashing", "COVERED", "hash function"),
                assessment("Discuss thread safety", "COVERED", "thread-safe"),
            ]
        ),
        "A hash function maps the key.",
        criteria,
    )
    assert [item.criterion for item in result.criterionAssessments] == criteria
    assert [item.status for item in result.criterionAssessments] == ["MISSING", "MISSING"]


def test_empty_draft_assessments_fail_without_retaining_dimension_scores(monkeypatch):
    result, _ = run_evaluation(
        monkeypatch,
        draft([], technicalAccuracy=10, clarity=10, depth=10),
        "A detailed answer.",
        ["Explain the concept"],
    )
    assert result.evaluationStatus == "FAILED"
    assert result.overallScore is None
    assert result.technicalAccuracy is None
    assert result.criterionAssessments == []
    assert result.strengths == []
    assert result.missingConcepts == []
    assert "unverified" in result.feedback


def test_llm_exception_returns_unverified_failure(monkeypatch):
    structured = MockStructuredLLM(error=RuntimeError("model unavailable"))
    monkeypatch.setattr(
        answer_service,
        "get_chat_model",
        lambda: MockChatModel(structured),
    )
    result = answer_service.evaluate_answer(
        "Question",
        "Candidate answer",
        "Engineer",
        "INTERMEDIATE",
        ["Criterion"],
    )
    assert result.evaluationStatus == "FAILED"
    assert result.technicalAccuracy is None
    assert result.criterionAssessments == []
    assert result.missingConcepts == []


def test_empty_and_duplicate_evaluation_criteria_are_rejected():
    with pytest.raises(ValidationError):
        AnswerEvaluationRequest(
            question="Question",
            candidateAnswer="Answer",
            targetRole="Engineer",
            difficulty="INTERMEDIATE",
            evaluationCriteria=[],
        )
    with pytest.raises(ValidationError):
        AnswerEvaluationRequest(
            question="Question",
            candidateAnswer="Answer",
            targetRole="Engineer",
            difficulty="INTERMEDIATE",
            evaluationCriteria=["Criterion", " criterion "],
        )


def test_evaluation_draft_requires_rationale(monkeypatch):
    with pytest.raises(ValidationError):
        AnswerEvaluationDraft.model_validate(
            draft(
                [
                    {
                        "criterion": "Explain hashing",
                        "status": "COVERED",
                        "evidence": "Hashing maps keys.",
                    }
                ]
            )
        )


def test_prompt_distinguishes_semantic_rationale_from_quote_validation(monkeypatch):
    result, mock = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment("Explain hashing", "PARTIALLY_COVERED", "hash function"),
                assessment("Describe collisions", "MISSING"),
                assessment("Discuss complexity", "MISSING"),
            ]
        ),
        "It uses a hash function.",
    )
    assert result.evaluationStatus == "COMPLETED"
    assert "Do not treat keyword mentions or verbatim phrases alone as proof" in mock.prompt
    assert "rationale must explain the actual substance" in mock.prompt


def test_invalid_follow_up_is_discarded_without_losing_valid_evaluation(monkeypatch):
    result, _ = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment("Explain hashing", "COVERED", "hash function"),
                assessment("Describe collisions", "COVERED", "separate chains"),
                assessment("Discuss complexity", "COVERED", "constant time"),
            ],
            suggestedFollowUp="Ask about concurrency?",
            suggestedFollowUpCriteria=["Concurrency", " concurrency  "],
        ),
        "A hash function; separate chains; constant time.",
    )
    assert result.evaluationStatus == "COMPLETED"
    assert result.overallScore is not None
    assert result.suggestedFollowUp is None
    assert result.suggestedFollowUpCriteria == []


def test_question_generation_returns_structured_questions_without_external_llm(
    monkeypatch,
):
    structured = MockStructuredLLM(
        result={
            "questions": [
                {
                    "questionText": "Explain a database transaction.",
                    "evaluationCriteria": ["Atomicity", "Isolation"],
                }
            ]
        }
    )
    monkeypatch.setattr(
        question_service,
        "get_chat_model",
        lambda: MockChatModel(structured),
    )
    result = question_service.generate_questions("Backend Engineer", "ADVANCED", 1)
    assert result[0].question_text == "Explain a database transaction."
    assert result[0].evaluation_criteria == ["Atomicity", "Isolation"]


@pytest.mark.parametrize(
    "question",
    [
        {"questionText": "  ", "evaluationCriteria": ["Criterion"]},
        {"questionText": "A valid question?", "evaluationCriteria": []},
        {"questionText": "A valid question?", "evaluationCriteria": [" "]},
        {
            "questionText": "A valid question?",
            "evaluationCriteria": ["Criterion", " criterion "],
        },
    ],
)
def test_generated_questions_reject_blank_or_duplicate_criteria(question):
    from app.schemas.question import GeneratedQuestion

    with pytest.raises(ValidationError):
        GeneratedQuestion.model_validate(question)


def test_question_generation_rejects_malformed_and_wrong_count_output(monkeypatch):
    malformed = MockStructuredLLM(result={"questions": [{"questionText": "No criteria"}]})
    monkeypatch.setattr(
        question_service,
        "get_chat_model",
        lambda: MockChatModel(malformed),
    )
    with pytest.raises(question_service.QuestionGenerationError):
        question_service.generate_questions("Engineer", "INTERMEDIATE", 1)

    wrong_count = MockStructuredLLM(
        result={
            "questions": [
                {
                    "questionText": "One question?",
                    "evaluationCriteria": ["Criterion"],
                }
            ]
        }
    )
    monkeypatch.setattr(
        question_service,
        "get_chat_model",
        lambda: MockChatModel(wrong_count),
    )
    with pytest.raises(question_service.QuestionGenerationError, match="unexpected"):
        question_service.generate_questions("Engineer", "INTERMEDIATE", 2)
