"""LLM provider boundary.

This is the ONE place inference touches the network. The prototype uses Google
Gemini; production swaps to Azure OpenAI by changing LLM_PROVIDER + keys, with no
change to callers. Everything else in Pulse (RAG, coaching, tagging, dashboard)
calls these three functions and is provider-agnostic.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .config import get_settings


@lru_cache
def _gemini_client():
    from google import genai

    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to backend/.env "
            "(free key: https://aistudio.google.com/apikey)."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def embed_texts(texts: list[str], *, task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Embed a batch of texts. `task` is RETRIEVAL_DOCUMENT for stored chunks
    and RETRIEVAL_QUERY for the incoming user query."""
    settings = get_settings()
    if not texts:
        return []
    if settings.llm_provider == "gemini":
        from google.genai import types

        client = _gemini_client()
        result = client.models.embed_content(
            model=settings.embed_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task,
                output_dimensionality=settings.embed_dim,
            ),
        )
        return [list(e.values) for e in result.embeddings]
    raise NotImplementedError(f"Embeddings for provider '{settings.llm_provider}' not wired yet.")


def generate(system_prompt: str, user_content: str, *, temperature: float = 0.6) -> str:
    """Single-shot text generation for the coached reply."""
    settings = get_settings()
    if settings.llm_provider == "gemini":
        from google.genai import types

        client = _gemini_client()
        resp = client.models.generate_content(
            model=settings.chat_model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
            ),
        )
        return (resp.text or "").strip()
    raise NotImplementedError(f"Generation for provider '{settings.llm_provider}' not wired yet.")


def generate_json(system_prompt: str, user_content: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Structured JSON generation used by passive tagging.

    `schema` is a JSON-schema-like dict; we ask the model for application/json and
    parse defensively."""
    settings = get_settings()
    if settings.llm_provider == "gemini":
        from google.genai import types

        client = _gemini_client()
        resp = client.models.generate_content(
            model=settings.tag_model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        try:
            return json.loads(resp.text or "{}")
        except json.JSONDecodeError:
            return {}
    raise NotImplementedError(f"Tagging for provider '{settings.llm_provider}' not wired yet.")
