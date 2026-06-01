"""LangGraph orchestration: retrieve → augment context for generation."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.config import Settings
from app.services.context_format import build_metadata_context, format_docs
from app.services.session_store import get_session
from app.services.vector_store import get_retriever


class RAGState(TypedDict):
    session_id: str
    question: str
    context: str
    sources: list[dict[str, Any]]
    video_metadata: str


def build_rag_graph(settings: Settings):
    graph = StateGraph(RAGState)

    def retrieve(state: RAGState):
        retriever = get_retriever(settings, state["session_id"])
        docs = retriever.invoke(state["question"])
        context, sources = format_docs(docs)
        session = get_session(state["session_id"])
        metadata = build_metadata_context(session) if session else ""
        return {
            "context": context,
            "sources": sources,
            "video_metadata": metadata,
        }

    graph.add_node("retrieve", retrieve)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", END)
    return graph.compile()


_graph_cache: dict[str, Any] = {}


def run_retrieval(settings: Settings, session_id: str, question: str) -> dict[str, Any]:
    key = settings.chroma_persist_dir
    if key not in _graph_cache:
        _graph_cache[key] = build_rag_graph(settings)
    app = _graph_cache[key]
    return app.invoke(
        {
            "session_id": session_id,
            "question": question,
            "context": "",
            "sources": [],
            "video_metadata": "",
        }
    )
