"""ChromaDB vector store with LangChain embeddings."""

from __future__ import annotations

import logging
import os
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import Settings
from app.services.embeddings_provider import get_embeddings

logger = logging.getLogger(__name__)


def collection_name(session_id: str) -> str:
    safe = session_id.replace("-", "")[:32]
    return f"reach_{safe}"


def chunk_and_index(
    settings: Settings,
    session_id: str,
    videos: list[dict[str, Any]],
) -> int:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    docs: list[Document] = []
    for video in videos:
        vid = video["video_id"]
        chunks = splitter.split_text(video["transcript"])
        for idx, text in enumerate(chunks):
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "video_id": vid,
                        "chunk_index": idx,
                        "platform": video["platform"],
                        "title": video["title"],
                        "creator": video["creator"],
                        "session_id": session_id,
                    },
                )
            )

    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    embeddings = get_embeddings(settings)
    Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=collection_name(session_id),
        persist_directory=settings.chroma_persist_dir,
    )
    return len(docs)


def get_retriever(settings: Settings, session_id: str, k: int | None = None):
    embeddings = get_embeddings(settings)
    k = k or settings.retrieval_k
    vectorstore = Chroma(
        collection_name=collection_name(session_id),
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )
