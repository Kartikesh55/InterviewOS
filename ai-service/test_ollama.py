from langchain_ollama import ChatOllama


llm = ChatOllama(
    model="qwen2.5:3b",
    temperature=0.2
)

response = llm.invoke(
    "Generate one intermediate-level Java interview question. "
    "Return only the question."
)

print(response.content)