from typing import Any

import pytest
from pydantic import ValidationError

from app.ai.services import answer_service, question_service
from app.schemas.evaluation import (
    AnswerEvaluationDraft,
    AnswerEvaluationRequest,
    CriterionAssessmentDraft,
)


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


@pytest.mark.parametrize(
    ("criteria", "answer", "evidence"),
    [
        (
            [
                "Load balancing",
                "Horizontal and vertical scaling",
                "Caching",
                "Error handling and fallback strategies",
                "Monitoring and alerting",
            ],
            (
                "Load balancing distributes requests across application instances. "
                "Horizontal scaling adds instances, while vertical scaling adds "
                "resources to each instance. Caching avoids repeated database reads. "
                "Retries, circuit breakers, and graceful degradation provide error "
                "handling and fallback strategies. Monitoring and alerting track "
                "latency, errors, and saturation."
            ),
            [
                "distributes requests across application instances",
                "Horizontal scaling adds instances",
                "Caching avoids repeated database reads",
                "Retries, circuit breakers, and graceful degradation",
                "Monitoring and alerting track latency, errors, and saturation",
            ],
        ),
        (
            [
                "Argon2, bcrypt, or PBKDF2",
                "Salting passwords",
                "Key derivation functions",
                "Secure storage and encryption",
                "Secure password handling",
            ],
            (
                "Argon2, bcrypt, and PBKDF2 are password hashing algorithms. "
                "Salting passwords prevents identical passwords from sharing a "
                "stored hash. These key derivation functions use configurable work "
                "factors. Secure storage keeps password hashes in the database, "
                "with encryption at rest protecting the storage. Secure password "
                "handling avoids logging plaintext credentials and uses TLS in transit."
            ),
            [
                "Argon2, bcrypt, and PBKDF2 are password hashing algorithms",
                "Salting passwords prevents identical passwords from sharing a stored hash",
                "key derivation functions use configurable work factors",
                "encryption at rest protecting the storage",
                "avoids logging plaintext credentials and uses TLS in transit",
            ],
        ),
    ],
    ids=["backend-scalability", "password-security"],
)
def test_representative_domain_answers_accept_valid_verbatim_evidence(
    monkeypatch,
    criteria,
    answer,
    evidence,
):
    result, _ = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment(criterion, "COVERED", quote)
                for criterion, quote in zip(criteria, evidence, strict=True)
            ]
        ),
        answer,
        criteria,
    )

    assert [item.criterion for item in result.criterionAssessments] == criteria
    assert [item.status for item in result.criterionAssessments] == ["COVERED"] * 5
    assert [item.evidence for item in result.criterionAssessments] == evidence
    assert result.completeness == 10


@pytest.mark.parametrize(
    ("criteria", "answer", "evidence", "unmatched_quote"),
    [
        (
            [
                "Load balancing",
                "Horizontal and vertical scaling",
                "Caching",
                "Error handling and fallback strategies",
                "Monitoring and alerting",
            ],
            (
                "Load balancing distributes requests across application instances. "
                "Horizontal scaling adds instances, while vertical scaling adds "
                "resources to each instance. Caching avoids repeated database reads. "
                "Retries, circuit breakers, and graceful degradation provide error "
                "handling and fallback strategies. Monitoring and alerting track "
                "latency, errors, and saturation."
            ),
            [
                "load balancing routes incoming traffic between service replicas",
                "Horizontal scaling adds instances",
                "Caching avoids repeated database reads",
                "Retries, circuit breakers, and graceful degradation",
                "Monitoring and alerting track latency, errors, and saturation",
            ],
            "load balancing routes incoming traffic between service replicas",
        ),
        (
            [
                "Argon2, bcrypt, or PBKDF2",
                "Salting passwords",
                "Key derivation functions",
                "Secure storage and encryption",
                "Secure password handling",
            ],
            (
                "Argon2, bcrypt, and PBKDF2 are password hashing algorithms. "
                "Salting passwords prevents identical passwords from sharing a "
                "stored hash. These key derivation functions use configurable work "
                "factors. Secure storage keeps password hashes in the database, "
                "with encryption at rest protecting the storage. Secure password "
                "handling avoids logging plaintext credentials and uses TLS in transit."
            ),
            [
                "the salt makes equal passwords produce different stored digests",
                "Salting passwords prevents identical passwords from sharing a stored hash",
                "key derivation functions use configurable work factors",
                "encryption at rest protecting the storage",
                "avoids logging plaintext credentials and uses TLS in transit",
            ],
            "the salt makes equal passwords produce different stored digests",
        ),
    ],
    ids=["backend-scalability", "password-security"],
)
def test_representative_answers_log_verbatim_evidence_downgrades_without_content(
    monkeypatch,
    caplog,
    criteria,
    answer,
    evidence,
    unmatched_quote,
):
    caplog.set_level("DEBUG", logger=answer_service.__name__)
    result, _ = run_evaluation(
        monkeypatch,
        draft(
            [
                assessment(criterion, "COVERED", quote)
                for criterion, quote in zip(criteria, evidence, strict=True)
            ]
        ),
        answer,
        criteria,
    )

    assert [item.status for item in result.criterionAssessments] == [
        "MISSING",
        "COVERED",
        "COVERED",
        "COVERED",
        "COVERED",
    ]
    assert result.completeness == 8
    assert "matched_exactly_once=True" in caplog.text
    assert "raw_status=COVERED" in caplog.text
    assert "evidence_valid=False" in caplog.text
    assert "final_status=MISSING" in caplog.text
    assert "reason=evidence_not_found_in_candidate_answer" in caplog.text
    assert answer not in caplog.text
    assert unmatched_quote not in caplog.text


def test_diagnostics_distinguish_llm_missing_from_evidence_validation_failure(
    caplog,
):
    caplog.set_level("DEBUG", logger=answer_service.__name__)
    assessments = [
        CriterionAssessmentDraft.model_validate(
            assessment("LLM marked missing", "MISSING", "matching phrase")
        ),
        CriterionAssessmentDraft.model_validate(
            assessment("Quote not found", "COVERED", "paraphrased quote")
        ),
    ]

    result = answer_service.validate_criterion_assessments(
        assessments,
        ["LLM marked missing", "Quote not found"],
        "A matching phrase appears here.",
    )

    assert [item.status for item in result] == ["MISSING", "MISSING"]
    assert "raw_status=MISSING evidence_valid=True final_status=MISSING reason=llm_marked_missing" in caplog.text
    assert "raw_status=COVERED evidence_valid=False final_status=MISSING reason=evidence_not_found_in_candidate_answer" in caplog.text
    assert "A matching phrase appears here." not in caplog.text
    assert "paraphrased quote" not in caplog.text


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
