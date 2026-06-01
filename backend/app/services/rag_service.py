"""LangChain streaming generation with LangGraph retrieval, citations, and memory."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.config import Settings
from app.services.context_format import build_metadata_context
from app.services.llm_provider import (
    _is_quota_error,
    gemini_models_to_try,
    get_llm,
    get_openai_llm,
)
from app.services.rag_graph import run_retrieval
from app.services.session_store import get_session, save_session

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Reach, an expert social-media growth analyst helping creators compare two videos.

Video A = YouTube (first URL ingested). Video B = Instagram Reel (second URL).

You have access to:
- Retrieved transcript chunks (tagged with video_id A or B and chunk_index)
- Structured metadata injected below (views, likes, comments, engagement rates, creators, hashtags, dates, duration)

Rules:
1. Answer using ONLY the provided context and metadata. If data is missing, say so clearly.
2. Always cite sources inline as [Video A, chunk N] or [Video B, chunk N] when referencing transcript content.
3. For engagement rate questions, use the precomputed values from metadata (formula: (likes+comments)/views×100).
4. For hook comparisons (first ~5 seconds), focus on the opening lines of transcripts and metadata duration.
5. Be concise, actionable, and creator-friendly.

Structured metadata:
{video_metadata}
"""

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        (
            "human",
            "Retrieved transcript context:\n{context}\n\n---\nUser question: {question}",
        ),
    ]
)


def _chat_history_messages(state, limit: int = 10) -> list[BaseMessage]:
    msgs: list[BaseMessage] = []
    for m in state.messages[-limit:]:
        if m["role"] == "user":
            msgs.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            msgs.append(AIMessage(content=m["content"]))
    return msgs


def _friendly_llm_error(exc: Exception, tried_models: list[str] | None = None) -> str:
    msg = str(exc)
    if _is_quota_error(exc):
        models = ", ".join(tried_models or [])
        return (
            "All Gemini models hit quota/rate limits"
            + (f" (tried: {models})" if models else "")
            + ". Wait 1–2 minutes, create a new key at https://aistudio.google.com/apikey, "
            "set GEMINI_MODEL=gemini-2.5-flash-lite in backend/.env, or add OPENAI_API_KEY "
            "and set AUTO_FALLBACK_OPENAI=true."
        )
    if "API key" in msg or "API_KEY" in msg:
        return "Invalid or missing GOOGLE_API_KEY. Check backend/.env."
    return f"LLM error: {msg[:400]}"


async def _stream_chain(chain, inputs: dict) -> AsyncIterator[str]:
    token_count = 0
    try:
        async for chunk in chain.astream(inputs):
            if chunk:
                token_count += 1
                yield chunk
    except Exception:
        text = await chain.ainvoke(inputs)
        if text:
            yield text
            return
        raise

    if token_count == 0:
        text = await chain.ainvoke(inputs)
        if text:
            yield text


async def _generate_answer(settings: Settings, inputs: dict) -> AsyncIterator[str]:
    """Try Gemini models in order; optional OpenAI fallback."""
    provider = (settings.llm_provider or "gemini").lower()
    tried: list[str] = []
    last_error: Exception | None = None

    if provider == "gemini":
        for model_name in gemini_models_to_try(settings):
            tried.append(model_name)
            llm = get_llm(settings, model=model_name)
            chain = RAG_PROMPT | llm | StrOutputParser()
            try:
                async for chunk in _stream_chain(chain, inputs):
                    yield chunk
                logger.info("Chat succeeded with Gemini model: %s", model_name)
                return
            except Exception as e:
                last_error = e
                if _is_quota_error(e):
                    logger.warning("Gemini quota for %s, trying next model", model_name)
                    continue
                raise

        if (
            settings.auto_fallback_openai
            and settings.openai_api_key
            and last_error
        ):
            logger.info("Falling back to OpenAI %s", settings.openai_model)
            tried.append(f"openai:{settings.openai_model}")
            chain = RAG_PROMPT | get_openai_llm(settings) | StrOutputParser()
            try:
                async for chunk in _stream_chain(chain, inputs):
                    yield chunk
                return
            except Exception as e:
                last_error = e

        if last_error:
            raise last_error
        raise RuntimeError("No LLM available")

    llm = get_llm(settings)
    chain = RAG_PROMPT | llm | StrOutputParser()
    async for chunk in _stream_chain(chain, inputs):
        yield chunk


async def stream_rag_answer(
    settings: Settings,
    session_id: str,
    question: str,
) -> AsyncIterator[str]:
    """Stream SSE payloads: status, sources, token, done, error."""
    state = get_session(session_id)
    if not state or not state.videos:
        yield json.dumps(
            {"type": "error", "content": "Session not found. Ingest videos first."}
        )
        return

    yield json.dumps({"type": "status", "content": "retrieving"})

    try:
        retrieval = await asyncio.to_thread(
            run_retrieval, settings, session_id, question
        )
    except Exception as e:
        logger.exception("Retrieval failed")
        yield json.dumps({"type": "error", "content": f"Retrieval failed: {e}"})
        return

    context_str = retrieval["context"]
    sources = retrieval["sources"]
    metadata_str = build_metadata_context(state)

    yield json.dumps({"type": "sources", "content": sources})
    yield json.dumps({"type": "status", "content": "generating"})

    inputs = {
        "context": context_str,
        "question": question,
        "video_metadata": metadata_str,
        "chat_history": _chat_history_messages(state),
    }

    full_answer = ""
    try:
        async for chunk in _generate_answer(settings, inputs):
            full_answer += chunk
            yield json.dumps({"type": "token", "content": chunk})
    except Exception as e:
        logger.exception("Chat generation failed")
        tried = gemini_models_to_try(settings) if (settings.llm_provider or "gemini") == "gemini" else []
        err = _friendly_llm_error(e, tried_models=tried)
        yield json.dumps({"type": "error", "content": err})
        return

    if not full_answer.strip():
        yield json.dumps(
            {
                "type": "error",
                "content": "The model returned an empty response. Check GEMINI_MODEL and API quota.",
            }
        )
        return

    state.messages.append({"role": "user", "content": question})
    state.messages.append(
        {"role": "assistant", "content": full_answer, "sources": sources}
    )
    save_session(state)
    yield json.dumps({"type": "done", "content": full_answer})
