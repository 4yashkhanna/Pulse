"""Coach pipeline: retrieve → build prompt → generate → persist → (tag)."""
from __future__ import annotations

from dataclasses import dataclass

from ..config import get_settings
from ..db import get_conn
from ..llm import generate
from ..rag.retrieve import Chunk, retrieve
from . import tagging
from .prompts import build_system_prompt


@dataclass
class CoachResult:
    reply: str
    conversation_id: str
    chunks: list[Chunk]
    tag: dict | None


def _format_history(history: list[dict], new_message: str) -> str:
    lines = []
    for turn in history[-8:]:
        who = "User" if turn.get("role") == "user" else "Coach"
        lines.append(f"{who}: {turn.get('content', '')}")
    lines.append(f"User: {new_message}")
    return "\n".join(lines)


def _ensure_conversation(conn, conversation_id: str | None, user_id: str, sector: str | None) -> str:
    if conversation_id:
        return conversation_id
    row = conn.execute(
        "INSERT INTO conversations (user_id, sector) VALUES (%s, %s) RETURNING id",
        (user_id, sector),
    ).fetchone()
    return str(row["id"])


def run_turn(
    *,
    message: str,
    user_id: str,
    sector: str | None,
    conversation_id: str | None,
    history: list[dict],
) -> CoachResult:
    settings = get_settings()

    # 1. Retrieve KPMG knowledge relevant to this turn.
    chunks = retrieve(message, industry=sector, k=6)

    # 2. Build the coaching system prompt and generate the reply.
    system_prompt = build_system_prompt(chunks, sector)
    reply = generate(system_prompt, _format_history(history, message))

    # 3. Persist conversation + both messages.
    with get_conn() as conn:
        conv_id = _ensure_conversation(conn, conversation_id, user_id, sector)
        user_msg = conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s,'user',%s) RETURNING id",
            (conv_id, message),
        ).fetchone()
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s,'assistant',%s)",
            (conv_id, reply),
        )
        conn.commit()
        user_msg_id = str(user_msg["id"])

    # 4. Passive tagging — synchronous in demo mode so the dashboard moves live.
    tag = None
    if settings.synchronous_tagging:
        tag = tagging.tag_and_store(
            conversation_id=conv_id,
            message_id=user_msg_id,
            user_id=user_id,
            user_message=message,
            coach_reply=reply,
        )

    return CoachResult(reply=reply, conversation_id=conv_id, chunks=chunks, tag=tag)
