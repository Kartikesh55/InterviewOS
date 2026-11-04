from langchain_ollama import ChatOllama


llm = ChatOllama(
    model="qwen2.5:3b",
    temperature=0.2
)


def generate_questions(
    target_role: str,
    difficulty: str,
    number_of_questions: int
) -> list[str]:

    prompt = f"""
    You are an experienced technical interviewer.

    Generate exactly {number_of_questions} technical interview questions
    for the role of {target_role}.

    Difficulty: {difficulty}

    Requirements:
    - Questions must be technically accurate.
    - Avoid duplicate questions.
    - Focus on practical engineering knowledge.
    - Return only a numbered list of questions.
    """

    response = llm.invoke(prompt)

    return [
        line.strip().lstrip("0123456789.-) ")
        for line in response.content.splitlines()
        if line.strip()
    ]