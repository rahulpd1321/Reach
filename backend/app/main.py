"""Reach RAG API — video ingest + streaming chat."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings
from app.models.schemas import (
    ChatHistoryResponse,
    ChatMessage,
    ChatRequest,
    IngestRequest,
    IngestResponse,
    SourceCitation,
    VideoMetadata,
)
from app.services import session_store
from app.services.rag_service import stream_rag_answer
from app.services.vector_store import chunk_and_index
from app.services.video_ingestion import ingest_pair

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    provider = (settings.llm_provider or "gemini").lower()
    model = settings.gemini_model if provider == "gemini" else settings.openai_model
    logger.info("Reach backend started (llm=%s, model=%s)", provider, model)
    yield


app = FastAPI(
    title="Reach RAG API",
    description="Compare YouTube vs Instagram Reels with RAG chat",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
_cors_origins = {
    settings.frontend_origin,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}
for origin in settings.frontend_origins.split(","):
    origin = origin.strip()
    if origin:
        _cors_origins.add(origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_cors_origins),
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    provider = (settings.llm_provider or "gemini").lower()
    if provider == "gemini":
        llm_ready = bool(settings.google_api_key)
    else:
        llm_ready = bool(settings.openai_api_key)
    return {
        "status": "ok",
        "llm_provider": provider,
        "llm_model": settings.gemini_model if provider == "gemini" else settings.openai_model,
        "llm_ready": llm_ready,
    }


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(body: IngestRequest):
    session_id = str(uuid.uuid4())
    try:
        raw_videos = ingest_pair(body.youtube_url, body.instagram_url)
    except Exception as e:
        logger.exception("Ingest failed")
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Strip transcript from API response payload (keep in memory for RAG)
    api_videos = []
    for v in raw_videos:
        api_videos.append({k: val for k, val in v.items() if k != "transcript"})

    state = session_store.create_session(session_id)
    state.videos = api_videos
    # Re-attach transcripts for indexing only
    indexing_videos = raw_videos

    try:
        count = chunk_and_index(settings, session_id, indexing_videos)
    except Exception as e:
        logger.exception("Indexing failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    state.chunks_indexed = count
    session_store.save_session(state)

    return IngestResponse(
        session_id=session_id,
        videos=[VideoMetadata(**v) for v in api_videos],
        chunks_indexed=count,
    )


@app.get("/api/session/{session_id}", response_model=ChatHistoryResponse)
async def get_session(session_id: str):
    state = session_store.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = [
        ChatMessage(
            role=m["role"],
            content=m["content"],
            sources=[
                SourceCitation(**s) for s in m.get("sources", [])
            ],
        )
        for m in state.messages
    ]
    return ChatHistoryResponse(
        session_id=session_id,
        messages=messages,
        videos=[VideoMetadata(**v) for v in state.videos],
    )


@app.post("/api/chat")
async def chat(body: ChatRequest):
    state = session_store.get_session(body.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found. Run ingest first.")

    async def event_generator():
        try:
            async for payload in stream_rag_answer(
                settings, body.session_id, body.message
            ):
                import json

                data = json.loads(payload)
                yield {"event": data.get("type", "message"), "data": payload}
        except ValueError as e:
            import json

            yield {
                "event": "error",
                "data": json.dumps({"type": "error", "content": str(e)}),
            }
        except Exception as e:
            logger.exception("Chat stream failed")
            import json

            yield {
                "event": "error",
                "data": json.dumps({"type": "error", "content": str(e)}),
            }

    return EventSourceResponse(event_generator())


# Demo URLs for quick testing (inputs can be hard-coded per spec)
DEMO_YOUTUBE = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
DEMO_INSTAGRAM = "https://www.instagram.com/reel/C8example/"


@app.get("/api/demo-urls")
async def demo_urls():
    return {
        "youtube_url": DEMO_YOUTUBE,
        "note": "Replace instagram_url with a public Reel URL you have access to",
    }
