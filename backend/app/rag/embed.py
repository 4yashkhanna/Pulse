"""Thin wrappers over the LLM provider for embeddings, with the right task type."""
from __future__ import annotations

from ..llm import embed_texts


def embed_documents(texts: list[str]) -> list[list[float]]:
    return embed_texts(texts, task="RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    return embed_texts([text], task="RETRIEVAL_QUERY")[0]
