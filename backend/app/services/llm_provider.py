"""LLM providers: Google Gemini (default) or OpenAI."""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel

from app.config import Settings

logger = logging.getLogger(__name__)

# Separate free-tier quotas per model (avoid exhausted gemini-2.0-flash)
DEFAULT_GEMINI_FALLBACKS = (
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-2.0-flash-lite",
)


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "429" in str(exc)
        or "resource_exhausted" in msg
        or "quota" in msg
        or "rate limit" in msg
    )


def gemini_models_to_try(settings: Settings) -> list[str]:
    """Primary model first, then fallbacks (deduped)."""
    extra = [
        m.strip()
        for m in (settings.gemini_model_fallbacks or "").split(",")
        if m.strip()
    ]
    ordered = [settings.gemini_model.strip(), *extra, *DEFAULT_GEMINI_FALLBACKS]
    seen: set[str] = set()
    out: list[str] = []
    for name in ordered:
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def build_gemini_llm(settings: Settings, model: str) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=settings.google_api_key,
        temperature=0.3,
        streaming=True,
    )


def get_llm(settings: Settings, model: str | None = None) -> BaseChatModel:
    provider = (settings.llm_provider or "gemini").lower()

    if provider == "gemini":
        if not settings.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY is required for Gemini. "
                "Get one at https://aistudio.google.com/apikey"
            )
        model_name = model or settings.gemini_model
        logger.info("Using Gemini model: %s", model_name)
        return build_gemini_llm(settings, model_name)

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        from langchain_openai import ChatOpenAI

        logger.info("Using OpenAI model: %s", settings.openai_model)
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.3,
            streaming=True,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use 'gemini' or 'openai'.")


def get_openai_llm(settings: Settings) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for OpenAI fallback.")
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
        streaming=True,
    )
