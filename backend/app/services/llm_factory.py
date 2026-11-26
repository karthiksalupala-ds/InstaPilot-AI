from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.core.config import get_settings


def get_chat_model(provider: str, model: str, temperature: float = 0.3) -> BaseChatModel:
    """Instantiate a configured Gemini or Groq chat model."""
    settings = get_settings()
    normalized = provider.lower().strip()

    if normalized == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        return ChatGoogleGenerativeAI(
            model=model or settings.default_llm_model,
            google_api_key=settings.gemini_api_key,
            temperature=temperature,
        )

    if normalized == "groq":
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        return ChatGroq(
            model=model or "llama-3.3-70b-versatile",
            api_key=settings.groq_api_key,  # type: ignore[arg-type]
            temperature=temperature,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")
