from functools import lru_cache

from langchain_ollama import ChatOllama

from app.core.config import get_settings


@lru_cache
def get_chat_model() -> ChatOllama:
    settings = get_settings()
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.2,
        client_kwargs={"timeout": settings.ollama_timeout_seconds},
    )
