from fastapi import FastAPI
from app.graphs.evaluation_graph import evaluation_graph
from app.models import (
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    AnswerEvaluationRequest,
    AnswerEvaluationResponse
)

from app.graphs.question_graph import question_graph

app = FastAPI(
    title="InterviewOS AI Service",
    description="AI-powered technical interview engine",
    version="1.0.0"
)


@app.get("/api/ai/health")
def health_check():
    return {
        "status": "UP",
        "service": "InterviewOS AI Service"
    }


@app.post(
    "/api/ai/generate-questions",
    response_model=QuestionGenerationResponse
)
def generate_interview_questions(
    request: QuestionGenerationRequest
):
    result = question_graph.invoke(
        {
            "target_role": request.targetRole,
            "difficulty": request.difficulty,
            "number_of_questions": request.numberOfQuestions,
            "questions": []
        }
    )

    return QuestionGenerationResponse(
        questions=result["questions"]
    )

@app.post(
    "/api/ai/evaluate-answer",
    response_model=AnswerEvaluationResponse
)
def evaluate_interview_answer(
    request: AnswerEvaluationRequest
):
    result = evaluation_graph.invoke(
        {
            "question": request.question,
            "candidate_answer": request.candidateAnswer,
            "target_role": request.targetRole,
            "difficulty": request.difficulty,
            "evaluation_criteria": request.evaluationCriteria,
            "evaluation": None
        }
    )

    return result["evaluation"]