from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.interview import (
    EvaluationStatus,
    Interview,
    InterviewAnswer,
    InterviewQuestion,
    QuestionCriterion,
    QuestionSource,
)


class MockGraph:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def invoke(self, state):
        self.calls.append(state)
        if self.error is not None:
            raise self.error
        return self.result


def generated_questions(count: int):
    return {
        "questions": [
            {
                "questionText": f"Explain concept {index}.",
                "evaluationCriteria": [f"Concept {index}", f"Trade-off {index}"],
            }
            for index in range(1, count + 1)
        ]
    }


def completed_evaluation(
    statuses=("COVERED", "COVERED"),
    *,
    follow_up="Describe a failure case?",
    follow_up_criteria=None,
):
    evidence = ("Concept 1 is supported.", "Trade-off 1 is explained.")
    return {
        "evaluation": {
            "evaluationStatus": "COMPLETED",
            "technicalAccuracy": 8,
            "completeness": 10,
            "clarity": 8,
            "depth": 7,
            "overallScore": 8.45,
            "criterionAssessments": [
                {
                    "criterion": "Concept 1",
                    "status": statuses[0],
                    "evidence": evidence[0] if statuses[0] != "MISSING" else "",
                },
                {
                    "criterion": "Trade-off 1",
                    "status": statuses[1],
                    "evidence": evidence[1] if statuses[1] != "MISSING" else "",
                },
            ],
            "strengths": [],
            "missingConcepts": [],
            "feedback": "Draft feedback.",
            "suggestedFollowUp": follow_up,
            "suggestedFollowUpCriteria": follow_up_criteria or ["Failure mode"],
        }
    }


def create_interview(client, count=2):
    response = client.post(
        "/api/interviews",
        json={
            "targetRole": "Backend Engineer",
            "difficulty": "INTERMEDIATE",
            "numberOfQuestions": count,
        },
    )
    assert response.status_code == 201
    return response.json()


def generate_for_interview(client, monkeypatch, count=2):
    from app.services import question_service

    graph = MockGraph(result=generated_questions(count))
    monkeypatch.setattr(question_service, "question_graph", graph)
    interview = create_interview(client, count)
    response = client.post(f"/api/interviews/{interview['id']}/questions")
    assert response.status_code == 200
    return interview, response.json(), graph


def test_health_and_create_interview_contract(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "UP", "service": "InterviewOS Backend"}

    response = client.post(
        "/api/interviews",
        json={
            "targetRole": "Backend Engineer",
            "difficulty": "ADVANCED",
            "numberOfQuestions": 1,
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "CREATED"
    assert response.json()["numberOfQuestions"] == 1
    assert response.json()["createdAt"].endswith("Z")


def test_existing_ai_utility_endpoints_remain_available(client, monkeypatch):
    from app.api.routes import ai

    question_graph = MockGraph(result=generated_questions(1))
    monkeypatch.setattr(ai, "question_graph", question_graph)
    generated = client.post(
        "/api/ai/generate-questions",
        json={
            "targetRole": "Backend Engineer",
            "difficulty": "INTERMEDIATE",
            "numberOfQuestions": 1,
        },
    )
    assert generated.status_code == 200
    assert generated.json()["questions"][0]["questionText"] == "Explain concept 1."
    assert generated.json()["questions"][0]["evaluationCriteria"] == [
        "Concept 1",
        "Trade-off 1",
    ]

    evaluation_graph = MockGraph(result=completed_evaluation())
    monkeypatch.setattr(ai, "evaluation_graph", evaluation_graph)
    evaluated = client.post(
        "/api/ai/evaluate-answer",
        json={
            "question": "Explain concept 1.",
            "candidateAnswer": "Concept 1 is supported. Trade-off 1 is explained.",
            "targetRole": "Backend Engineer",
            "difficulty": "INTERMEDIATE",
            "evaluationCriteria": ["Concept 1", "Trade-off 1"],
        },
    )
    assert evaluated.status_code == 200
    assert evaluated.json()["evaluationStatus"] == "COMPLETED"
    assert evaluated.json()["suggestedFollowUpCriteria"] == ["Failure mode"]


@pytest.mark.parametrize(
    "payload",
    [
        {"targetRole": "  ", "difficulty": "INTERMEDIATE", "numberOfQuestions": 1},
        {"targetRole": "Role", "difficulty": "INVALID", "numberOfQuestions": 1},
        {"targetRole": "Role", "difficulty": "BEGINNER", "numberOfQuestions": 0},
        {"targetRole": "Role", "difficulty": "BEGINNER", "numberOfQuestions": 21},
    ],
)
def test_invalid_interview_requests_return_400(client, payload):
    response = client.post("/api/interviews", json=payload)
    assert response.status_code == 400
    assert response.json()["message"] == "Validation failed"


def test_generated_questions_and_ordered_criteria_are_persisted_idempotently(
    client,
    monkeypatch,
    session_factory,
):
    interview, questions, graph = generate_for_interview(client, monkeypatch)
    assert [question["questionOrder"] for question in questions] == [1, 2]
    assert questions[0]["evaluationCriteria"] == ["Concept 1", "Trade-off 1"]
    assert questions[0]["source"] == "GENERATED"

    repeat = client.post(f"/api/interviews/{interview['id']}/questions")
    assert repeat.status_code == 200
    assert repeat.json() == questions
    assert len(graph.calls) == 1

    with session_factory() as session:
        saved = session.scalar(
            select(InterviewQuestion).where(
                InterviewQuestion.id == UUID(questions[0]["id"])
            )
        )
        assert [item.criterion for item in saved.criteria] == [
            "Concept 1",
            "Trade-off 1",
        ]
        assert saved.interview_id == UUID(interview["id"])


def test_malformed_generation_is_rejected_without_persisting_questions(
    client,
    monkeypatch,
    session_factory,
):
    from app.services import question_service

    graph = MockGraph(result={"questions": [{"questionText": "No criteria"}]})
    monkeypatch.setattr(question_service, "question_graph", graph)
    interview = create_interview(client, 1)

    response = client.post(f"/api/interviews/{interview['id']}/questions")
    assert response.status_code == 502
    assert client.get(f"/api/interviews/{interview['id']}").json()["questions"] == []


def test_lifecycle_transitions_and_question_progression(
    client,
    monkeypatch,
):
    interview, questions, _ = generate_for_interview(client, monkeypatch)
    interview_id = interview["id"]
    assert client.post(f"/api/interviews/{interview_id}/start").json()["status"] == "IN_PROGRESS"
    assert client.post(f"/api/interviews/{interview_id}/start").status_code == 409
    assert client.get(f"/api/interviews/{interview_id}/current-question").json()["id"] == questions[0]["id"]

    next_question = client.post(f"/api/interviews/{interview_id}/next-question")
    assert next_question.status_code == 200
    assert next_question.json()["questionOrder"] == 2
    assert client.post(f"/api/interviews/{interview_id}/next-question").status_code == 409
    assert client.post(f"/api/interviews/{interview_id}/complete").json()["status"] == "COMPLETED"
    assert client.post(f"/api/interviews/{interview_id}/complete").status_code == 409


def test_start_without_questions_and_missing_interview_are_rejected(client):
    interview = create_interview(client, 1)
    assert client.post(f"/api/interviews/{interview['id']}/start").status_code == 409
    missing_id = UUID(int=1)
    assert client.get(f"/api/interviews/{missing_id}").status_code == 404
    assert client.post(f"/api/interviews/{missing_id}/start").status_code == 404


def test_failed_evaluation_keeps_answer_and_marks_failed(
    client,
    monkeypatch,
    session_factory,
):
    from app.services import answer_service

    interview, questions, _ = generate_for_interview(client, monkeypatch, 1)
    interview_id = interview["id"]
    question_id = questions[0]["id"]
    client.post(f"/api/interviews/{interview_id}/start")
    monkeypatch.setattr(
        answer_service,
        "evaluation_graph",
        MockGraph(error=RuntimeError("Ollama unavailable")),
    )

    response = client.post(
        f"/api/interviews/{interview_id}/questions/{question_id}/answers",
        json={"candidateAnswer": "Candidate answer."},
    )
    assert response.status_code == 201
    assert response.json()["evaluationStatus"] == "FAILED"
    assert response.json()["overallScore"] is None
    assert response.json()["candidateAnswer"] == "Candidate answer."

    with session_factory() as session:
        saved = session.scalar(select(InterviewAnswer))
        assert saved.candidate_answer == "Candidate answer."
        assert saved.evaluation_status == EvaluationStatus.FAILED


def test_completed_evaluation_is_persisted_and_follow_up_replaces_next_question(
    client,
    monkeypatch,
    session_factory,
):
    from app.services import answer_service

    interview, questions, _ = generate_for_interview(client, monkeypatch, 2)
    interview_id = interview["id"]
    first, second = questions
    client.post(f"/api/interviews/{interview_id}/start")
    graph = MockGraph(result=completed_evaluation(
        statuses=("COVERED", "PARTIALLY_COVERED"),
        follow_up="Describe a failure case?",
        follow_up_criteria=["Failure handling", "Recovery behavior"],
    ))
    monkeypatch.setattr(answer_service, "evaluation_graph", graph)
    response = client.post(
        f"/api/interviews/{interview_id}/questions/{first['id']}/answers",
        json={"candidateAnswer": "Concept 1 is supported. Trade-off 1 is explained."},
    )
    assert response.status_code == 201
    result = response.json()
    assert result["evaluationStatus"] == "COMPLETED"
    assert result["completeness"] == 7.5
    assert result["overallScore"] == 7.7
    assert result["criterionAssessments"][1]["status"] == "PARTIALLY_COVERED"
    assert [item["criterion"] for item in result["criterionAssessments"]] == [
        "Concept 1",
        "Trade-off 1",
    ]

    details = client.get(f"/api/interviews/{interview_id}").json()
    assert len(details["questions"]) == 2
    replaced = details["questions"][1]
    assert replaced["id"] == second["id"]
    assert replaced["questionOrder"] == 2
    assert replaced["questionText"] == "Describe a failure case?"
    assert replaced["source"] == "FOLLOW_UP"
    assert replaced["evaluationCriteria"] == ["Failure handling", "Recovery behavior"]

    with session_factory() as session:
        answer = session.scalar(select(InterviewAnswer))
        assert answer.evaluation_status == EvaluationStatus.COMPLETED
        assert len(answer.assessments) == 2
        assert [item.criterion for item in answer.follow_up_criteria] == [
            "Failure handling",
            "Recovery behavior",
        ]
        assert session.query(InterviewQuestion).filter_by(
            interview_id=UUID(interview_id)
        ).count() == 2


def test_good_answer_keeps_scheduled_next_question(
    client,
    monkeypatch,
):
    from app.services import answer_service

    interview, questions, _ = generate_for_interview(client, monkeypatch, 2)
    client.post(f"/api/interviews/{interview['id']}/start")
    monkeypatch.setattr(
        answer_service,
        "evaluation_graph",
        MockGraph(result=completed_evaluation()),
    )
    client.post(
        f"/api/interviews/{interview['id']}/questions/{questions[0]['id']}/answers",
        json={"candidateAnswer": "Concept 1 is supported. Trade-off 1 is explained."},
    )
    details = client.get(f"/api/interviews/{interview['id']}").json()
    assert details["questions"][1]["questionText"] == questions[1]["questionText"]
    assert details["questions"][1]["source"] == "GENERATED"


def test_invalid_follow_up_criteria_are_discarded_without_failing_evaluation(
    client,
    monkeypatch,
):
    from app.services import answer_service

    interview, questions, _ = generate_for_interview(client, monkeypatch, 2)
    client.post(f"/api/interviews/{interview['id']}/start")
    invalid_follow_up = completed_evaluation(
        statuses=("COVERED", "PARTIALLY_COVERED"),
        follow_up="Ask about concurrency?",
        follow_up_criteria=["Concurrency", " concurrency "],
    )
    monkeypatch.setattr(
        answer_service,
        "evaluation_graph",
        MockGraph(result=invalid_follow_up),
    )
    result = client.post(
        f"/api/interviews/{interview['id']}/questions/{questions[0]['id']}/answers",
        json={"candidateAnswer": "Concept 1 is supported. Trade-off 1 is explained."},
    ).json()
    assert result["evaluationStatus"] == "COMPLETED"
    assert result["suggestedFollowUp"] is None
    assert result["suggestedFollowUpCriteria"] == []
    details = client.get(f"/api/interviews/{interview['id']}").json()
    assert details["questions"][1]["questionText"] == questions[1]["questionText"]


def test_answers_require_current_question_owned_by_active_interview(
    client,
    monkeypatch,
):
    interview, questions, _ = generate_for_interview(client, monkeypatch, 2)
    other, other_questions, _ = generate_for_interview_for_second(
        client,
        monkeypatch,
        2,
    )
    client.post(f"/api/interviews/{interview['id']}/start")
    wrong_interview = client.post(
        f"/api/interviews/{interview['id']}/questions/{other_questions[0]['id']}/answers",
        json={"candidateAnswer": "Text"},
    )
    assert wrong_interview.status_code == 404
    client.post(f"/api/interviews/{interview['id']}/next-question")
    non_current = client.post(
        f"/api/interviews/{interview['id']}/questions/{questions[0]['id']}/answers",
        json={"candidateAnswer": "Text"},
    )
    assert non_current.status_code == 409
    client.post(f"/api/interviews/{interview['id']}/complete")
    completed = client.post(
        f"/api/interviews/{interview['id']}/questions/{questions[1]['id']}/answers",
        json={"candidateAnswer": "Text"},
    )
    assert completed.status_code == 409
    assert other["status"] == "CREATED"


def generate_for_interview_for_second(client, monkeypatch, count):
    from app.services import question_service

    graph = MockGraph(result=generated_questions(count))
    monkeypatch.setattr(question_service, "question_graph", graph)
    interview = create_interview(client, count)
    response = client.post(f"/api/interviews/{interview['id']}/questions")
    assert response.status_code == 200
    return interview, response.json(), graph


def test_duplicate_answers_and_final_slot_follow_up_are_handled(
    client,
    monkeypatch,
):
    from app.services import answer_service

    interview, questions, _ = generate_for_interview(client, monkeypatch, 1)
    client.post(f"/api/interviews/{interview['id']}/start")
    monkeypatch.setattr(
        answer_service,
        "evaluation_graph",
        MockGraph(result=completed_evaluation(
            statuses=("MISSING", "MISSING"),
            follow_up="Extra question?",
        )),
    )
    path = (
        f"/api/interviews/{interview['id']}/questions/"
        f"{questions[0]['id']}/answers"
    )
    first = client.post(path, json={"candidateAnswer": "No concepts."})
    assert first.status_code == 201
    assert client.post(path, json={"candidateAnswer": "Second attempt."}).status_code == 409
    assert client.get(f"/api/interviews/{interview['id']}").json()["questions"][0][
        "source"
    ] == "GENERATED"


def test_report_aggregates_persisted_answer_without_new_evaluation(
    client,
    monkeypatch,
    session_factory,
):
    from app.services import answer_service

    interview, questions, _ = generate_for_interview(client, monkeypatch, 1)
    client.post(f"/api/interviews/{interview['id']}/start")
    graph = MockGraph(result=completed_evaluation())
    monkeypatch.setattr(answer_service, "evaluation_graph", graph)
    client.post(
        f"/api/interviews/{interview['id']}/questions/{questions[0]['id']}/answers",
        json={"candidateAnswer": "Concept 1 is supported. Trade-off 1 is explained."},
    )
    report = client.get(f"/api/interviews/{interview['id']}/report")
    assert report.status_code == 200
    saved_answer = report.json()["questions"][0]["answers"][0]
    assert saved_answer["evaluationStatus"] == "COMPLETED"
    assert saved_answer["technicalAccuracy"] == 8
    assert saved_answer["completeness"] == 10
    assert saved_answer["clarity"] == 8
    assert saved_answer["depth"] == 7
    assert saved_answer["overallScore"] == 8.45
    assert saved_answer["criterionAssessments"] == [
        {
            "criterion": "Concept 1",
            "status": "COVERED",
            "evidence": "Concept 1 is supported.",
        },
        {
            "criterion": "Trade-off 1",
            "status": "COVERED",
            "evidence": "Trade-off 1 is explained.",
        },
    ]
    assert saved_answer["strengths"] == ["Concept 1", "Trade-off 1"]
    assert saved_answer["missingConcepts"] == []
    assert len(graph.calls) == 1
    assert report.json()["createdAt"].endswith("Z")

    with session_factory() as session:
        persisted_answer = session.scalar(select(InterviewAnswer))
        assert persisted_answer.evaluation_status == EvaluationStatus.COMPLETED
        assert persisted_answer.technical_accuracy == 8
        assert persisted_answer.completeness == 10
        assert persisted_answer.clarity == 8
        assert persisted_answer.depth == 7
        assert persisted_answer.overall_score == 8.45
        assert [
            (item.criterion, item.status.value, item.evidence)
            for item in persisted_answer.assessments
        ] == [
            ("Concept 1", "COVERED", "Concept 1 is supported."),
            ("Trade-off 1", "COVERED", "Trade-off 1 is explained."),
        ]
