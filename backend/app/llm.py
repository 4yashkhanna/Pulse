"""LLM provider boundary.

This is the ONE place inference touches the network. The prototype uses Google
Gemini; production swaps to Azure OpenAI by changing LLM_PROVIDER + keys, with no
change to callers. Everything else in Pulse (RAG, coaching, tagging, dashboard)
calls these three functions and is provider-agnostic.
"""
from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any, Callable, TypeVar

from .config import get_settings

T = TypeVar("T")


class RateLimited(Exception):
    """Raised when the provider rate-limits us after retries are exhausted."""


def _is_transient(exc: Exception) -> bool:
    """Rate limits (429) and temporary server errors (503 overloaded) — both worth a retry."""
    s = str(exc).lower()
    return any(
        tok in s
        for tok in ("429", "resource_exhausted", "exhausted", "503", "unavailable", "overloaded", "high demand")
    )


def _with_retry(fn: Callable[[], T], *, attempts: int = 4, base_delay: float = 2.0) -> T:
    """Retry transient provider errors with exponential backoff; re-raise other errors."""
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if _is_transient(exc):
                if i == attempts - 1:
                    raise RateLimited(str(exc)) from exc
                time.sleep(base_delay * (2**i))
                continue
            raise


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
        result = _with_retry(
            lambda: client.models.embed_content(
                model=settings.embed_model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task,
                    output_dimensionality=settings.embed_dim,
                ),
            )
        )
        return [list(e.values) for e in result.embeddings]
    raise NotImplementedError(f"Embeddings for provider '{settings.llm_provider}' not wired yet.")


def generate(
    system_prompt: str,
    user_content: str,
    *,
    temperature: float = 0.6,
    attachments: list[tuple[str, bytes]] | None = None,
) -> str:
    """Single-shot text generation for the coached reply.

    `attachments` is a list of (mime_type, raw_bytes) — images or PDFs the user uploaded.
    Gemini reads them natively as additional content parts."""
    settings = get_settings()
    if settings.llm_provider == "gemini":
        from google.genai import types

        client = _gemini_client()
        contents: list = [user_content]
        for mime, data in attachments or []:
            contents.append(types.Part.from_bytes(data=data, mime_type=mime))
        resp = _with_retry(
            lambda: client.models.generate_content(
                model=settings.chat_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                ),
            )
        )
        return (resp.text or "").strip()
    raise NotImplementedError(f"Generation for provider '{settings.llm_provider}' not wired yet.")


def generate_stream(
    system_prompt: str,
    user_content: str,
    *,
    temperature: float = 0.6,
    attachments: list[tuple[str, bytes]] | None = None,
):
    """Streaming variant of generate(): yields text deltas as they arrive.

    Transient errors are retried only on the initial call (before any tokens have
    been yielded); once streaming has begun a failure surfaces to the caller."""
    settings = get_settings()
    if settings.llm_provider == "gemini":
        from google.genai import types

        client = _gemini_client()
        contents: list = [user_content]
        for mime, data in attachments or []:
            contents.append(types.Part.from_bytes(data=data, mime_type=mime))
        stream = _with_retry(
            lambda: client.models.generate_content_stream(
                model=settings.chat_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                ),
            )
        )
        for event in stream:
            if event.text:
                yield event.text
        return
    raise NotImplementedError(f"Streaming for provider '{settings.llm_provider}' not wired yet.")


async def generate_with_tools(
    system_prompt: str,
    user_content: str,
    *,
    sessions: list[Any],
    temperature: float = 0.6,
    attachments: list[tuple[str, bytes]] | None = None,
) -> tuple[str, list[str]]:
    """Tool-augmented generation: the model may call MCP tools mid-turn.

    `sessions` is a list of live MCP ClientSessions (one per connected provider). The
    google-genai SDK natively accepts them in `tools=` and runs automatic function
    calling — it executes the tool calls against the sessions and returns the final text.

    Returns (reply_text, tool_names_called) so the chat layer can surface which tools ran.
    Falls back to a plain reply if there are no sessions.
    """
    settings = get_settings()
    if settings.llm_provider != "gemini":
        raise NotImplementedError(f"Tool use for provider '{settings.llm_provider}' not wired yet.")
    from google.genai import types

    client = _gemini_client()
    contents: list = [user_content]
    for mime, data in attachments or []:
        contents.append(types.Part.from_bytes(data=data, mime_type=mime))

    resp = await client.aio.models.generate_content(
        model=settings.chat_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            tools=sessions,  # MCP ClientSessions — SDK handles the call loop
        ),
    )
    # Recover which tools the model actually invoked from the AFC history.
    called: list[str] = []
    for item in getattr(resp, "automatic_function_calling_history", None) or []:
        for part in getattr(item, "parts", None) or []:
            fc = getattr(part, "function_call", None)
            if fc and fc.name and fc.name not in called:
                called.append(fc.name)
    return (resp.text or "").strip(), called


def generate_json(system_prompt: str, user_content: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Structured JSON generation used by passive tagging.

    `schema` is a JSON-schema-like dict; we ask the model for application/json and
    parse defensively."""
    settings = get_settings()
    if settings.llm_provider == "gemini":
        from google.genai import types

        client = _gemini_client()
        resp = _with_retry(
            lambda: client.models.generate_content(
                model=settings.tag_model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
        )
        try:
            return json.loads(resp.text or "{}")
        except json.JSONDecodeError:
            return {}
    raise NotImplementedError(f"Tagging for provider '{settings.llm_provider}' not wired yet.")
