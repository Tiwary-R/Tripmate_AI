"""Free LLMs: local Ollama (default) or Groq's free tier."""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from travel_agent.config import GROQ_API_KEY, GROQ_MODEL, LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL


@lru_cache
def get_llm(temperature: float = 0.3) -> BaseChatModel:
    if LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq

        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
        return ChatGroq(model=GROQ_MODEL, temperature=temperature, api_key=GROQ_API_KEY)
    if LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=temperature)
    raise RuntimeError("No LLM configured (demo mode).")


def get_structured_llm(schema):
    """LLM that returns an instance of `schema` via tool calling (most reliable for Llama models)."""
    return get_llm(0).with_structured_output(schema, method="function_calling")
