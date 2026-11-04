from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.ai.services.answer_service import evaluate_answer
from app.schemas.evaluation import AnswerEvaluationResponse


class EvaluationState(TypedDict):
    question: str
    candidate_answer: str
    target_role: str
    difficulty: str
    evaluation_criteria: list[str]
    evaluation: AnswerEvaluationResponse | None


def evaluate_answer_node(
    state: EvaluationState,
) -> dict[str, AnswerEvaluationResponse]:
    return {
        "evaluation": evaluate_answer(
            question=state["question"],
            candidate_answer=state["candidate_answer"],
            target_role=state["target_role"],
            difficulty=state["difficulty"],
            evaluation_criteria=state["evaluation_criteria"],
        )
    }


def build_evaluation_graph():
    graph = StateGraph(EvaluationState)
    graph.add_node("evaluate_answer", evaluate_answer_node)
    graph.add_edge(START, "evaluate_answer")
    graph.add_edge("evaluate_answer", END)
    return graph.compile()


evaluation_graph = build_evaluation_graph()
