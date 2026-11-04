import logging

from langchain_ollama import ChatOllama

from app.models import GeneratedQuestion, QuestionGenerationResponse


logger = logging.getLogger(__name__)

llm = ChatOllama(
    model="qwen2.5:3b",
    temperature=0.2
)

structured_llm = llm.with_structured_output(
    QuestionGenerationResponse,
    method="json_schema"
)


def generate_questions(
    target_role: str,
    difficulty: str,
    number_of_questions: int
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
        raw_response = structured_llm.invoke(prompt)
        response = QuestionGenerationResponse.model_validate(raw_response)
    except Exception as error:
        logger.exception("Question generation failed")
        raise QuestionGenerationError(
            "AI service returned invalid generated questions"
        ) from error

    if len(response.questions) != number_of_questions:
        raise QuestionGenerationError(
            "AI service returned an unexpected number of questions"
        )
    return response.questions


class QuestionGenerationError(RuntimeError):
    pass
