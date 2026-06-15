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


# JSON-schema keys Gemini's function-declaration schema understands. Real MCP tools ship
# richer JSON Schema (additionalProperties, $schema, $ref, oneOf, …); the google-genai
# auto-adapter chokes on some of it (e.g. a boolean `additionalProperties`), so we sanitize
# tool schemas ourselves and run the function-call loop manually.
_SCHEMA_KEYS = {
    "type", "format", "description", "nullable", "enum", "items",
    "properties", "required", "anyOf", "minItems", "maxItems",
    "minimum", "maximum", "minLength", "maxLength", "pattern", "default",
}
_MAX_TOOL_TURNS = 6


def _sanitize_schema(node: Any) -> Any:
    """Coerce an MCP tool inputSchema into the subset Gemini accepts.

    Drops unsupported keys, ignores boolean schema values (e.g. additionalProperties: true),
    collapses union `type` lists to their first concrete type, and recurses."""
    if not isinstance(node, dict):
        return None
    out: dict[str, Any] = {}
    for key, val in node.items():
        if key not in _SCHEMA_KEYS:
            continue
        if key == "properties" and isinstance(val, dict):
            cleaned = {k: _sanitize_schema(v) for k, v in val.items()}
            out["properties"] = {k: v for k, v in cleaned.items() if v is not None}
        elif key == "items":
            child = _sanitize_schema(val)
            if child is not None:
                out["items"] = child
        elif key == "anyOf" and isinstance(val, list):
            variants = [c for c in (_sanitize_schema(v) for v in val) if c is not None]
            if variants:
                out["anyOf"] = variants
        elif key == "type" and isinstance(val, list):
            concrete = next((t for t in val if t != "null"), None)
            if concrete:
                out["type"] = concrete
        else:
            out[key] = val
    # Gemini requires every array to declare `items` and every object a `properties`
    # map; supply permissive defaults when the source schema's were unsupported/empty.
    if out.get("type") == "array" and "items" not in out:
        out["items"] = {"type": "object", "properties": {}}
    if out.get("type") == "object" and "properties" not in out:
        out["properties"] = {}
    return out or None


async def generate_with_tools(
    system_prompt: str,
    user_content: str,
    *,
    sessions: list[Any],
    temperature: float = 0.6,
    attachments: list[tuple[str, bytes]] | None = None,
) -> tuple[str, list[str]]:
    """Tool-augmented generation: the model may call MCP tools mid-turn.

    `sessions` is a list of live MCP ClientSessions (one per connected provider). We list
    each session's tools, expose them to Gemini as function declarations (with sanitized
    schemas), and run the call loop ourselves — dispatching each function call to the
    owning session and feeding the result back until the model produces a final answer.

    Returns (reply_text, tool_names_called) so the chat layer can surface which tools ran.
    """
    settings = get_settings()
    if settings.llm_provider != "gemini":
        raise NotImplementedError(f"Tool use for provider '{settings.llm_provider}' not wired yet.")
    from google.genai import types

    # Discover tools across all sessions; map each tool name to its owning session.
    declarations: list[Any] = []
    owner: dict[str, Any] = {}
    for session in sessions:
        listed = await session.list_tools()
        for tool in listed.tools:
            params = _sanitize_schema(tool.inputSchema) or {"type": "object", "properties": {}}
            declarations.append(
                types.FunctionDeclaration(
                    name=tool.name,
                    description=(tool.description or "")[:1024],
                    parameters=params,
                )
            )
            owner[tool.name] = session

    client = _gemini_client()
    parts: list = [types.Part.from_text(text=user_content)]
    for mime, data in attachments or []:
        parts.append(types.Part.from_bytes(data=data, mime_type=mime))
    history: list = [types.Content(role="user", parts=parts)]

    # Tool turns make several model calls; on a rate limit (429) the SDK otherwise sleeps
    # for the server's retry-after (~60s) per call, which looks like a hang. Cap retries so
    # a throttled turn fails fast and the chat layer can fall back cleanly.
    http_options = types.HttpOptions(
        timeout=45_000,
        retry_options=types.HttpRetryOptions(attempts=2, http_status_codes=[503]),
    )
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
        tools=[types.Tool(function_declarations=declarations)] if declarations else None,
        # We drive the loop; don't let the SDK try to auto-execute (it can't reach MCP).
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        http_options=http_options,
    )

    called: list[str] = []
    for _ in range(_MAX_TOOL_TURNS):
        resp = await client.aio.models.generate_content(
            model=settings.chat_model, contents=history, config=config
        )
        candidate = (resp.candidates or [None])[0]
        content = getattr(candidate, "content", None)
        fn_calls = [
            p.function_call
            for p in (getattr(content, "parts", None) or [])
            if getattr(p, "function_call", None)
        ]
        if not fn_calls:
            return (resp.text or "").strip(), called

        history.append(content)  # the model's tool-call turn
        tool_parts: list = []
        for fc in fn_calls:
            if fc.name not in called:
                called.append(fc.name)
            session = owner.get(fc.name)
            try:
                result = await session.call_tool(fc.name, dict(fc.args or {}))
                payload = _mcp_result_text(result)
            except Exception as exc:  # noqa: BLE001 — report tool failure to the model
                payload = f"Tool error: {exc}"
            tool_parts.append(
                types.Part.from_function_response(name=fc.name, response={"result": payload})
            )
        history.append(types.Content(role="user", parts=tool_parts))

    # Exhausted the tool budget — make one final call without tools for a clean answer.
    final = await client.aio.models.generate_content(
        model=settings.chat_model,
        contents=history,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt, temperature=temperature, http_options=http_options
        ),
    )
    return (final.text or "").strip(), called


def _mcp_result_text(result: Any) -> str:
    """Flatten an MCP call_tool result into text for the model."""
    if getattr(result, "structuredContent", None):
        return json.dumps(result.structuredContent)[:8000]
    chunks: list[str] = []
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if text:
            chunks.append(text)
    return ("\n".join(chunks) or "(no content)")[:8000]


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
