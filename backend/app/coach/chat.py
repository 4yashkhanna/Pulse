"""Coach pipeline (org-scoped): retrieve → prompt → generate → persist → tag.

Two entry points share the same preparation:
- run_turn        — blocking; returns the full reply (legacy /chat endpoint)
- run_turn_stream — generator of SSE-ready events; the reply streams token by token,
                    then the turn is persisted and tagged (the tag arrives as a final event)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import re

from ..config import get_settings
from ..connections import store as conn_store
from ..db import get_conn
from ..llm import generate, generate_stream
from ..rag.retrieve import Chunk, retrieve
from . import skills as skills_mod
from . import tagging
from .prompts import build_system_prompt, tools_addendum

SLASH_RE = re.compile(r"^/([a-z0-9][a-z0-9-]*)\s*", re.IGNORECASE)


@dataclass
class CoachResult:
    reply: str
    conversation_id: str
    title: str
    chunks: list[Chunk]
    tag: dict | None


@dataclass
class PreparedTurn:
    text: str
    attach_note: str
    conversation_id: str
    title: str
    history: list[dict]
    chunks: list[Chunk]
    system_prompt: str
    skill: dict | None = None  # {"name","command"} when a skill is pinned to the chat


def _org_config(conn, org_id: str) -> dict:
    r = conn.execute(
        "SELECT name, maturity_stage, maturity_label, coach_prompt FROM organizations WHERE id = %s",
        (org_id,),
    ).fetchone()
    return dict(r) if r else {}


def _history(conn, conversation_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id = %s "
        "ORDER BY created_at, (role = 'assistant')",
        (conversation_id,),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def _format_history(history: list[dict], new_message: str) -> str:
    lines = []
    for turn in history[-8:]:
        who = "User" if turn["role"] == "user" else "Coach"
        lines.append(f"{who}: {turn['content']}")
    lines.append(f"User: {new_message}")
    return "\n".join(lines)


def _prepare_turn(
    *,
    message: str,
    org_id: str,
    user_id: str,
    conversation_id: str | None,
    team_id: str | None,
    project_id: str | None,
    attachments: list[tuple[str, bytes, str]],
) -> PreparedTurn:
    """Everything before generation: org config, history, conversation row, retrieval."""
    attach_note = (
        "\n\n[attached: " + ", ".join(name for _, _, name in attachments) + "]"
        if attachments
        else ""
    )
    # What we embed/tag/store as the user's text. If they sent only files, use a placeholder.
    text = message.strip() or "(see attached file)"

    skill: dict | None = None
    with get_conn() as conn:
        cfg = _org_config(conn, org_id)
        if conversation_id:
            history = _history(conn, conversation_id)
            row = conn.execute(
                "SELECT title, project_id FROM conversations WHERE id = %s", (conversation_id,)
            ).fetchone()
            title = row["title"] if row else "New chat"
            # The conversation's own project is authoritative for retrieval.
            project_id = str(row["project_id"]) if row and row["project_id"] else None
            skill = skills_mod.skill_for_conversation(conn, conversation_id)
        else:
            history = []
            # A new chat starting with /command pins that skill to the conversation.
            m = SLASH_RE.match(text)
            if m:
                skill = skills_mod.resolve_command(conn, org_id, m.group(1))
                if skill:
                    text = text[m.end():].strip() or f"Let's begin. Use the {skill['name']} process."
            base_title = text if skill else (message.strip() or (attachments[0][2] if attachments else "New chat"))
            if skill:
                base_title = f"/{skill['command']} · {base_title}"
            title = (base_title[:48] + "…") if len(base_title) > 48 else base_title
            conv = conn.execute(
                "INSERT INTO conversations (org_id, user_id, project_id, skill_id, title) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (org_id, user_id, project_id, skill["id"] if skill else None, title),
            ).fetchone()
            conversation_id = str(conv["id"])
            conn.commit()

    # Folders imported into this project that the user has been granted access to.
    folder_ids: list[str] = []
    if project_id:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT pfi.folder_id FROM project_folder_imports pfi
                JOIN folder_access fa ON fa.folder_id = pfi.folder_id
                  AND fa.user_id = %s AND fa.status = 'granted'
                WHERE pfi.project_id = %s
                """,
                (user_id, project_id),
            ).fetchall()
            folder_ids = [str(r["folder_id"]) for r in rows]

    # Retrieve layered knowledge (org + team-general + project + imported folders).
    chunks = retrieve(
        text, org_id=org_id, team_id=team_id, project_id=project_id, folder_ids=folder_ids, k=6
    )
    system_prompt = build_system_prompt(
        chunks,
        org_name=cfg.get("name", "the organization"),
        maturity_stage=cfg.get("maturity_stage"),
        maturity_label=cfg.get("maturity_label"),
        coach_prompt=cfg.get("coach_prompt"),
    )
    if skill:
        system_prompt += f"\n\n{skill['body']}"
    return PreparedTurn(
        text=text,
        attach_note=attach_note,
        conversation_id=conversation_id,
        title=title,
        history=history,
        chunks=chunks,
        system_prompt=system_prompt,
        skill={"name": skill["name"], "command": skill["command"]} if skill else None,
    )


def _mcp_reply(
    prep: PreparedTurn,
    *,
    user_id: str,
    attachments: list[tuple[str, bytes, str]],
) -> tuple[str, list[str]] | None:
    """Tool-augmented reply when the user has connected tools (non-streaming, legacy /chat).

    Hands the model the cached tool menu and lets it decide whether any tool is needed; a
    provider's MCP server is only contacted if the model actually calls one. Returns
    (reply, tools_used), or None if the user has no reachable tools (caller falls back to
    the normal text path).

    Runs the async MCP stack via asyncio.run — safe here because the streaming route drives
    this generator in a threadpool with no running event loop.
    """
    import asyncio

    from ..connections.mcp_client import tool_menu, tool_sessions
    from ..llm import generate_with_tools

    async def _run() -> tuple[str, list[str]] | None:
        async with tool_sessions(user_id) as sessions:
            decls = await tool_menu(user_id, sessions)
            if not decls:
                return None
            labels = list(dict.fromkeys(d.label for d in decls))

            async def dispatch(provider: str, name: str, args: dict) -> str:
                return await sessions.call_tool(provider, name, args)

            return await generate_with_tools(
                prep.system_prompt + tools_addendum(labels),
                _format_history(prep.history, prep.text),
                declarations=[vars(d) for d in decls],
                dispatch=dispatch,
                attachments=[(mime, data) for mime, data, _ in attachments],
            )

    try:
        return asyncio.run(_run())
    except Exception:  # noqa: BLE001 — never let a tool failure break the turn
        return None


def _mcp_stream(
    prep: PreparedTurn,
    *,
    user_id: str,
    attachments: list[tuple[str, bytes, str]],
) -> Iterator[dict]:
    """Drive the async tool-aware *streaming* generation from this sync SSE generator.

    Yields the same event dicts as llm.generate_with_tools_stream
    ({"type":"delta"|"tool_used", ...}). Opens a turn-scoped MCP session pool and hands the
    model the cached tool menu; a tool server is contacted only if the model calls a tool.
    Yields nothing if the user has no reachable tools (or setup fails before any output) —
    the caller then falls back to the plain streaming path.

    The whole async generation runs as a single task on a private event loop in a background
    thread, with events handed back through a queue. This is deliberate: MCP's transport uses
    anyio cancel scopes that must be entered and exited in the *same* task, so we can't drive
    the generator step-by-step from this (synchronous, threadpool-run) caller — we let it run
    start-to-finish in one task and just consume what it emits.
    """
    import asyncio
    import queue
    import threading

    from ..connections.mcp_client import tool_menu, tool_sessions
    from ..llm import generate_with_tools_stream

    events: queue.Queue = queue.Queue(maxsize=256)
    _DONE = object()

    async def _drive():
        try:
            async with tool_sessions(user_id) as sessions:
                decls = await tool_menu(user_id, sessions)
                if not decls:
                    return
                labels = list(dict.fromkeys(d.label for d in decls))

                async def dispatch(provider: str, name: str, args: dict) -> str:
                    return await sessions.call_tool(provider, name, args)

                async for ev in generate_with_tools_stream(
                    prep.system_prompt + tools_addendum(labels),
                    _format_history(prep.history, prep.text),
                    declarations=[vars(d) for d in decls],
                    dispatch=dispatch,
                    attachments=[(mime, data) for mime, data, _ in attachments],
                ):
                    events.put(("ev", ev))
        except Exception as exc:  # noqa: BLE001 — relayed to the consumer below
            events.put(("err", exc))
        finally:
            events.put((_DONE, None))

    def _run():
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_drive())
        finally:
            loop.close()

    worker = threading.Thread(target=_run, name="mcp-stream", daemon=True)
    worker.start()

    err: Exception | None = None
    while True:
        kind, payload = events.get()
        if kind is _DONE:
            break
        if kind == "err":
            err = payload  # defer: drain until _DONE, then surface
            continue
        yield payload
    worker.join()
    # An error here means the user HAS usable tools but the tool-aware generation failed
    # (an empty menu returns cleanly with no error). Surface it rather than letting the
    # caller fall back to a tool-less answer that would falsely claim it can't reach their
    # tools — an honest "something went wrong" beats a confident lie.
    if err is not None:
        # Map a provider rate-limit (429) to RateLimited so the route shows the accurate
        # "wait a few seconds" message instead of a generic error.
        from ..llm import RateLimited, _is_transient

        if not isinstance(err, RateLimited) and _is_transient(err):
            raise RateLimited(str(err)) from err
        raise err


def _persist_turn(prep: PreparedTurn, message: str, reply: str) -> str:
    """Store both messages, bump the conversation timestamp; returns the user message id.

    The two inserts use clock_timestamp() (real wall-clock, which advances within a
    transaction) rather than the column default now() (transaction-start time, identical for
    every row in the same transaction). Otherwise the user and assistant messages get the
    SAME created_at and `ORDER BY created_at` is a tie that Postgres breaks arbitrarily —
    which is why a reloaded conversation sometimes showed the reply above the question.
    """
    with get_conn() as conn:
        user_msg = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) "
            "VALUES (%s,'user',%s, clock_timestamp()) RETURNING id",
            (prep.conversation_id, message + prep.attach_note),
        ).fetchone()
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) "
            "VALUES (%s,'assistant',%s, clock_timestamp())",
            (prep.conversation_id, reply),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = now() WHERE id = %s", (prep.conversation_id,)
        )
        conn.commit()
        return str(user_msg["id"])


def _tag_turn(prep: PreparedTurn, *, org_id: str, user_id: str, user_msg_id: str, reply: str) -> dict | None:
    """Passive tagging. Never let a tagging failure (e.g. a rate limit) break the
    user's reply — the message is already saved."""
    try:
        return tagging.tag_and_store(
            org_id=org_id,
            user_id=user_id,
            conversation_id=prep.conversation_id,
            message_id=user_msg_id,
            user_message=prep.text,
            coach_reply=reply,
        )
    except Exception:  # noqa: BLE001
        return None


def run_turn(
    *,
    message: str,
    org_id: str,
    user_id: str,
    conversation_id: str | None,
    team_id: str | None = None,
    project_id: str | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> CoachResult:
    settings = get_settings()
    attachments = attachments or []
    prep = _prepare_turn(
        message=message, org_id=org_id, user_id=user_id, conversation_id=conversation_id,
        team_id=team_id, project_id=project_id, attachments=attachments,
    )
    reply: str | None = None
    if conn_store.connected_providers(user_id):
        tool_result = _mcp_reply(prep, user_id=user_id, attachments=attachments)
        if tool_result is not None:
            reply = tool_result[0]
    if reply is None:
        reply = generate(
            prep.system_prompt,
            _format_history(prep.history, prep.text),
            attachments=[(mime, data) for mime, data, _ in attachments],
        )
    user_msg_id = _persist_turn(prep, message, reply)

    tag = None
    if settings.synchronous_tagging:
        tag = _tag_turn(prep, org_id=org_id, user_id=user_id, user_msg_id=user_msg_id, reply=reply)

    return CoachResult(
        reply=reply, conversation_id=prep.conversation_id, title=prep.title,
        chunks=prep.chunks, tag=tag,
    )


def run_turn_stream(
    *,
    message: str,
    org_id: str,
    user_id: str,
    conversation_id: str | None,
    team_id: str | None = None,
    project_id: str | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> Iterator[dict]:
    """Yields events for the SSE endpoint:
    {"type":"meta", conversation_id, title, retrieved}   — once, immediately
    {"type":"delta", "text": ...}                        — per token batch
    {"type":"done"}                                      — reply persisted
    {"type":"tag", "tag": {...}}                         — fired signals (after the reply)
    """
    settings = get_settings()
    attachments = attachments or []
    prep = _prepare_turn(
        message=message, org_id=org_id, user_id=user_id, conversation_id=conversation_id,
        team_id=team_id, project_id=project_id, attachments=attachments,
    )
    yield {
        "type": "meta",
        "conversation_id": prep.conversation_id,
        "title": prep.title,
        "skill": prep.skill,
        "retrieved": [
            {"source": c.source, "scope": c.scope, "similarity": round(c.similarity, 3)}
            for c in prep.chunks
        ],
    }

    reply: str | None = None
    # If the user has connected tools, expose the (cached) tool menu and let the model
    # decide whether any are needed. The reply streams token-by-token like the normal path;
    # a tool server is contacted only if the model actually calls one — so "hello" never
    # touches the user's tools. If nothing is produced (no reachable tools), we fall through
    # to the plain streaming path below.
    if conn_store.connected_providers(user_id):
        stream_parts: list[str] = []
        for ev in _mcp_stream(prep, user_id=user_id, attachments=attachments):
            if ev["type"] == "delta":
                stream_parts.append(ev["text"])
            yield ev
        if stream_parts:
            reply = "".join(stream_parts).strip()

    if reply is None:
        parts: list[str] = []
        for delta in generate_stream(
            prep.system_prompt,
            _format_history(prep.history, prep.text),
            attachments=[(mime, data) for mime, data, _ in attachments],
        ):
            parts.append(delta)
            yield {"type": "delta", "text": delta}
        reply = "".join(parts).strip()

    user_msg_id = _persist_turn(prep, message, reply)
    yield {"type": "done"}

    # The user already has the full reply on screen — tagging cost is now invisible.
    if settings.synchronous_tagging:
        tag = _tag_turn(prep, org_id=org_id, user_id=user_id, user_msg_id=user_msg_id, reply=reply)
        if tag:
            yield {"type": "tag", "tag": tag}
