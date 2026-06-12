"""Coach pipeline (org-scoped): retrieve → prompt → generate → persist → tag.

Two entry points share the same preparation:
- run_turn        — blocking; returns the full reply (legacy /chat endpoint)
- run_turn_stream — generator of SSE-ready events; the reply streams token by token,
                    then the turn is persisted and tagged (the tag arrives as a final event)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from ..config import get_settings
from ..db import get_conn
from ..llm import generate, generate_stream
from ..rag.retrieve import Chunk, retrieve
from . import tagging
from .prompts import build_system_prompt


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


def _org_config(conn, org_id: str) -> dict:
    r = conn.execute(
        "SELECT name, maturity_stage, maturity_label, coach_prompt FROM organizations WHERE id = %s",
        (org_id,),
    ).fetchone()
    return dict(r) if r else {}


def _history(conn, conversation_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id = %s ORDER BY created_at",
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
        else:
            history = []
            base_title = message.strip() or (attachments[0][2] if attachments else "New chat")
            title = (base_title[:48] + "…") if len(base_title) > 48 else base_title
            conv = conn.execute(
                "INSERT INTO conversations (org_id, user_id, project_id, title) VALUES (%s,%s,%s,%s) RETURNING id",
                (org_id, user_id, project_id, title),
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
    return PreparedTurn(
        text=text,
        attach_note=attach_note,
        conversation_id=conversation_id,
        title=title,
        history=history,
        chunks=chunks,
        system_prompt=system_prompt,
    )


def _persist_turn(prep: PreparedTurn, message: str, reply: str) -> str:
    """Store both messages, bump the conversation timestamp; returns the user message id."""
    with get_conn() as conn:
        user_msg = conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s,'user',%s) RETURNING id",
            (prep.conversation_id, message + prep.attach_note),
        ).fetchone()
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s,'assistant',%s)",
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
        "retrieved": [
            {"source": c.source, "scope": c.scope, "similarity": round(c.similarity, 3)}
            for c in prep.chunks
        ],
    }

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
