from fastapi import APIRouter

from app.ai.graphs.evaluation_graph import evaluation_graph
from app.ai.graphs.question_graph import question_graph
from app.ai.services.question_service import QuestionGenerationError
from app.core.exceptions import QuestionGenerationFailed
from app.schemas.evaluation import AnswerEvaluationRequest, AnswerEvaluationResponse
from app.schemas.question import (
    QuestionGenerationRequest,
    QuestionGenerationResponse,
)


router = APIRouter(prefix="/api/ai", tags=["AI workflows"])


@router.post(
    "/generate-questions",
    response_model=QuestionGenerationResponse,
)
@router.post("/questions", response_model=QuestionGenerationResponse)
def generate_questions(request: QuestionGenerationRequest):
    try:
        result = question_graph.invoke(
            {
                "target_role": request.target_role,
                "difficulty": request.difficulty,
                "number_of_questions": request.number_of_questions,
                "questions": [],
            }
        )
        return QuestionGenerationResponse(questions=result["questions"])
    except QuestionGenerationError as error:
        raise QuestionGenerationFailed(str(error)) from error


@router.post(
    "/evaluate-answer",
    response_model=AnswerEvaluationResponse,
)
def evaluate_candidate_answer(request: AnswerEvaluationRequest):
    result = evaluation_graph.invoke(
        {
            "question": request.question,
            "candidate_answer": request.candidateAnswer,
            "target_role": request.targetRole,
            "difficulty": request.difficulty,
            "evaluation_criteria": request.evaluationCriteria,
            "evaluation": None,
        }
    )
    return result["evaluation"]
