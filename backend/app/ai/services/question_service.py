import logging

from app.ai.llm import get_chat_model
from app.schemas.question import GeneratedQuestion, QuestionGenerationResponse


logger = logging.getLogger(__name__)


def generate_questions(
    target_role: str,
    difficulty: str,
    number_of_questions: int,
) -> list[GeneratedQuestion]:
    prompt = f"""
You are an experienced technical interviewer.

Generate exactly {number_of_questions} technical interview questions for
the role of {target_role}.

Difficulty: {difficulty}

For every question, provide:
- questionText: a concise, technically accurate question
- evaluationCriteria: a non-empty list of specific, independently assessable
  concepts that a good answer should address

Avoid duplicate questions. Criteria must be relevant to their question, concrete,
and useful for evaluating a candidate answer. Return only the structured output.
"""
    try:
        structured_llm = get_chat_model().with_structured_output(
            QuestionGenerationResponse,
            method="json_schema",
        )
        response = QuestionGenerationResponse.model_validate(
            structured_llm.invoke(prompt)
        )
    except Exception as error:
        logger.exception("Question generation failed")
        raise QuestionGenerationError(
            "AI model returned invalid generated questions"
        ) from error

    if len(response.questions) != number_of_questions:
        raise QuestionGenerationError(
            "AI model returned an unexpected number of questions"
        )
    return response.questions


class QuestionGenerationError(RuntimeError):
    pass
