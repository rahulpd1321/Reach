"""Embedding providers: OpenAI or local FastEmbed (no PyTorch)."""

from __future__ import annotations

import logging
from typing import List

from langchain_core.embeddings import Embeddings

from app.config import Settings

logger = logging.getLogger(__name__)

_embeddings: Embeddings | None = None


class FastEmbedEmbeddings(Embeddings):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [vec.tolist() for vec in self._model.embed(texts)]

    def embed_query(self, text: str) -> List[float]:
        return list(self._model.embed([text]))[0].tolist()


def get_embeddings(settings: Settings) -> Embeddings:
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    if settings.use_openai_embeddings and settings.openai_api_key:
        from langchain_openai import OpenAIEmbeddings

        _embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )
        logger.info("Using OpenAI embeddings: %s", settings.openai_embedding_model)
    else:
        _embeddings = FastEmbedEmbeddings()
        logger.info("Using FastEmbed local embeddings (bge-small-en-v1.5)")
    return _embeddings
