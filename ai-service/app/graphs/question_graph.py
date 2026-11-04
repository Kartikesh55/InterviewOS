from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.services.question_service import generate_questions


class QuestionState(TypedDict):
    target_role: str
    difficulty: str
    number_of_questions: int
    questions: list[str]


def generate_question_node(state: QuestionState):
    questions = generate_questions(
        target_role=state["target_role"],
        difficulty=state["difficulty"],
        number_of_questions=state["number_of_questions"]
    )

    return {
        "questions": questions
    }


def build_question_graph():
    graph = StateGraph(QuestionState)

    graph.add_node("generate_questions", generate_question_node)

    graph.add_edge(START, "generate_questions")
    graph.add_edge("generate_questions", END)

    return graph.compile()


question_graph = build_question_graph()