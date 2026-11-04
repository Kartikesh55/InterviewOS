from typing import Any

import pytest

from pydantic import ValidationError

from app.models import AnswerEvaluationDraft, AnswerEvaluationRequest
from app.services import answer_service


CRITERIA = ["Explain hashing", "Describe collision handling", "Discuss complexity"]


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


def draft(
    assessments: list[dict[str, str]],
    *,
    technical_accuracy: float = 8,
    clarity: float = 7,
    depth: float = 6,
    **extra: Any,
) -> dict[str, Any]:
    result = {
        "technicalAccuracy": technical_accuracy,
        "clarity": clarity,
        "depth": depth,
        "criterionAssessments": assessments,
        "feedback": "Model feedback is not used as a source of assessment facts.",
        "suggestedFollowUp": "How would you test this implementation?",
    }
    result.update(extra)
    return result


def assessment(
    criterion: str,
    status: str,
    evidence: str = "",
    rationale: str | None = None,
) -> dict[str, str]:
    if rationale is None:
        rationale = {
            "COVERED": "The answer sufficiently explains the criterion.",
            "PARTIALLY_COVERED": "The answer addresses only part of the criterion.",
            "MISSING": "The answer does not meaningfully address the criterion.",
        }[status]
    return {
        "criterion": criterion,
        "status": status,
        "evidence": evidence,
        "rationale": rationale,
    }


def run_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    result: Any,
    answer: str,
    criteria: list[str] | None = None,
):
    monkeypatch.setattr(
        answer_service,
        "structured_llm",
        MockStructuredLLM(result=result),
    )
    return answer_service.evaluate_answer(
        question="Explain a hash map.",
        candidate_answer=answer,
        target_role="Software Engineer",
        difficulty="Intermediate",
        evaluation_criteria=criteria or CRITERIA,
    )


def test_strong_answer_scores_all_valid_criteria(monkeypatch: pytest.MonkeyPatch):
    answer = (
        "A hash map maps keys to values using a hash function. "
        "Collisions can be handled with chaining. "
        "Lookup is O(1) on average."
    )
    result = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment("Explain hashing", "COVERED", "maps keys to values"),
                assessment("Describe collision handling", "COVERED", "with chaining"),
                assessment("Discuss complexity", "COVERED", "O(1) on average"),
            ],
            technical_accuracy=8,
            clarity=9,
            depth=7,
        ),
        answer,
    )

    assert [item.status for item in result.criterionAssessments] == ["COVERED"] * 3
    assert result.completeness == 10
    assert result.overallScore == 8.6
    assert result.strengths == CRITERIA
    assert result.missingConcepts == []


def test_average_answer_distinguishes_covered_partial_and_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    result = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment("Explain hashing", "COVERED", "uses a hash function"),
                assessment("Describe collision handling", "PARTIALLY_COVERED", "collisions"),
                assessment("Discuss complexity", "MISSING"),
            ]
        ),
        "A map uses a hash function. It must handle collisions.",
    )

    assert [item.status for item in result.criterionAssessments] == [
        "COVERED",
        "PARTIALLY_COVERED",
        "MISSING",
    ]
    assert result.completeness == 5
    assert result.strengths == ["Explain hashing"]
    assert result.missingConcepts == ["Discuss complexity"]
    assert "partially addressed" in result.feedback
    assert "Discuss complexity" in result.feedback


def test_weak_answer_marks_only_unaddressed_criteria_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    result = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment("Explain hashing", "MISSING"),
                assessment("Describe collision handling", "MISSING"),
                assessment("Discuss complexity", "PARTIALLY_COVERED", "constant time"),
            ]
        ),
        "It can be constant time.",
    )

    assert [item.status for item in result.criterionAssessments] == [
        "MISSING",
        "MISSING",
        "PARTIALLY_COVERED",
    ]
    assert result.completeness == 1.67
    assert result.missingConcepts == ["Explain hashing", "Describe collision handling"]


def test_fabricated_evidence_is_not_trusted(monkeypatch: pytest.MonkeyPatch):
    result = run_evaluation(
        monkeypatch,
        draft([assessment("Explain hashing", "COVERED", "uses a balanced tree")]),
        "A hash map uses a hash function.",
        ["Explain hashing"],
    )

    assert result.criterionAssessments[0].status == "MISSING"
    assert result.criterionAssessments[0].evidence == ""
    assert result.missingConcepts == ["Explain hashing"]
    assert result.strengths == []


def test_invented_criterion_is_discarded(monkeypatch: pytest.MonkeyPatch):
    result = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment("Explain hashing", "COVERED", "hash function"),
                assessment("Discuss thread safety", "COVERED", "thread safe"),
            ]
        ),
        "A hash function maps the key.",
        ["Explain hashing", "Discuss complexity"],
    )

    assert [item.criterion for item in result.criterionAssessments] == [
        "Explain hashing",
        "Discuss complexity",
    ]
    assert [item.status for item in result.criterionAssessments] == [
        "COVERED",
        "MISSING",
    ]


def test_duplicate_criterion_assessment_is_rejected(monkeypatch: pytest.MonkeyPatch):
    result = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment("Explain hashing", "COVERED", "hash function"),
                assessment("Explain hashing", "COVERED", "hash function"),
                assessment("Discuss complexity", "MISSING"),
            ]
        ),
        "A hash function maps keys.",
        ["Explain hashing", "Discuss complexity"],
    )

    assert [item.status for item in result.criterionAssessments] == [
        "MISSING",
        "MISSING",
    ]


def test_partial_evidence_allows_only_case_and_whitespace_differences(
    monkeypatch: pytest.MonkeyPatch,
):
    answer = "It handles COLLISIONS\nwith chaining."
    result = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment(
                    "Describe collision handling",
                    "PARTIALLY_COVERED",
                    "handles collisions with   chaining.",
                )
            ]
        ),
        answer,
        ["Describe collision handling"],
    )

    assert result.criterionAssessments[0].status == "PARTIALLY_COVERED"
    assert result.criterionAssessments[0].evidence == "handles COLLISIONS\nwith chaining."


def test_strengths_are_derived_and_cannot_contradict_missing_criteria(
    monkeypatch: pytest.MonkeyPatch,
):
    result = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment("Explain hashing", "MISSING"),
                assessment("Discuss complexity", "COVERED", "O(1) average"),
            ],
            strengths=["Explain hashing was an excellent strength"],
        ),
        "Lookup is O(1) average.",
        ["Explain hashing", "Discuss complexity"],
    )

    assert result.strengths == ["Discuss complexity"]
    assert result.missingConcepts == ["Explain hashing"]
    assert "Explain hashing" in result.feedback
    assert "excellent strength" not in result.feedback


@pytest.mark.parametrize(
    "mock",
    [
        MockStructuredLLM(result=None),
        MockStructuredLLM(error=RuntimeError("model unavailable")),
    ],
)
def test_malformed_or_failed_llm_returns_explicit_fallback(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    mock: MockStructuredLLM,
):
    monkeypatch.setattr(answer_service, "structured_llm", mock)

    result = answer_service.evaluate_answer(
        question="Explain a hash map.",
        candidate_answer="A hash map stores values.",
        target_role="Software Engineer",
        difficulty="Intermediate",
        evaluation_criteria=["Explain hashing"],
    )

    assert result.overallScore == 0
    assert result.technicalAccuracy == 0
    assert result.completeness == 0
    assert result.clarity == 0
    assert result.depth == 0
    assert result.criterionAssessments == []
    assert result.strengths == []
    assert result.missingConcepts == []
    assert "could not be completed" in result.feedback
    assert "unverified" in result.feedback
    assert "Answer evaluation failed" in caplog.text


def test_empty_assessments_with_high_dimension_scores_use_fallback(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    result = run_evaluation(
        monkeypatch,
        draft(
            [],
            technical_accuracy=10,
            clarity=10,
            depth=10,
        ),
        "A detailed answer.",
        ["Explain the concept"],
    )

    assert result.technicalAccuracy == 0
    assert result.completeness == 0
    assert result.clarity == 0
    assert result.depth == 0
    assert result.overallScore == 0
    assert result.criterionAssessments == []
    assert result.strengths == []
    assert result.missingConcepts == []
    assert "unverified" in result.feedback
    assert "no criterion assessments" in caplog.text


def test_draft_requires_rationale_for_each_assessment():
    with pytest.raises(ValidationError):
        AnswerEvaluationDraft.model_validate(
            {
                "technicalAccuracy": 8,
                "clarity": 8,
                "depth": 8,
                "criterionAssessments": [
                    {
                        "criterion": "Explain the concept",
                        "status": "COVERED",
                        "evidence": "Here is an explanation.",
                    }
                ],
                "feedback": "Feedback",
            }
        )


def test_prompt_distinguishes_explanation_from_keyword_evidence(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_llm = MockStructuredLLM(
        result=draft(
            [
                assessment(
                    "Explain hashing",
                    "PARTIALLY_COVERED",
                    "hash function",
                    "The answer names the hash function but does not explain how it is used.",
                )
            ]
        )
    )
    monkeypatch.setattr(answer_service, "structured_llm", mock_llm)

    answer_service.evaluate_answer(
        question="Explain a hash map.",
        candidate_answer="It uses a hash function.",
        target_role="Software Engineer",
        difficulty="Intermediate",
        evaluation_criteria=["Explain hashing"],
    )

    assert "COVERED: the candidate demonstrates the concept" in mock_llm.prompt
    assert "PARTIALLY_COVERED: the candidate mentions or explains only part" in mock_llm.prompt
    assert "MISSING: the candidate does not meaningfully address" in mock_llm.prompt
    assert "Do not treat keyword mentions or verbatim phrases alone as proof" in mock_llm.prompt


def test_empty_and_duplicate_criteria_are_rejected():
    with pytest.raises(ValueError):
        AnswerEvaluationRequest(
            question="Question",
            candidateAnswer="Answer",
            targetRole="Engineer",
            difficulty="Intermediate",
            evaluationCriteria=[],
        )

    with pytest.raises(ValueError):
        AnswerEvaluationRequest(
            question="Question",
            candidateAnswer="Answer",
            targetRole="Engineer",
            difficulty="Intermediate",
            evaluationCriteria=["Explain hashing", " explain   HASHING "],
        )


def test_fastapi_evaluation_route_keeps_existing_response_contract(
    monkeypatch: pytest.MonkeyPatch,
):
    from app.main import evaluate_interview_answer

    monkeypatch.setattr(
        answer_service,
        "structured_llm",
        MockStructuredLLM(
            result=draft(
                [assessment("Explain hashing", "COVERED", "hash function")],
            )
        ),
    )
    result = evaluate_interview_answer(
        AnswerEvaluationRequest(
            question="Explain a hash map.",
            candidateAnswer="It uses a hash function.",
            targetRole="Software Engineer",
            difficulty="Intermediate",
            evaluationCriteria=["Explain hashing"],
        )
    )

    assert result.completeness == 10
    assert result.model_dump().keys() == {
        "technicalAccuracy",
        "completeness",
        "clarity",
        "depth",
        "overallScore",
        "criterionAssessments",
        "strengths",
        "missingConcepts",
        "feedback",
        "suggestedFollowUp",
    }
