"""Coach pipeline (org-scoped): retrieve → prompt → generate → persist → tag."""
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
    title: str
    chunks: list[Chunk]
    tag: dict | None


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


def run_turn(
    *, message: str, org_id: str, user_id: str, conversation_id: str | None
) -> CoachResult:
    settings = get_settings()

    # Fetch org config + history, create conversation if needed.
    with get_conn() as conn:
        cfg = _org_config(conn, org_id)
        if conversation_id:
            history = _history(conn, conversation_id)
            title_row = conn.execute(
                "SELECT title FROM conversations WHERE id = %s", (conversation_id,)
            ).fetchone()
            title = title_row["title"] if title_row else "New chat"
        else:
            history = []
            title = (message[:48] + "…") if len(message) > 48 else message
            conv = conn.execute(
                "INSERT INTO conversations (org_id, user_id, title) VALUES (%s,%s,%s) RETURNING id",
                (org_id, user_id, title),
            ).fetchone()
            conversation_id = str(conv["id"])
            conn.commit()

    # Retrieve org knowledge + generate.
    chunks = retrieve(message, org_id=org_id, k=6)
    system_prompt = build_system_prompt(
        chunks,
        org_name=cfg.get("name", "the organization"),
        maturity_stage=cfg.get("maturity_stage"),
        maturity_label=cfg.get("maturity_label"),
        coach_prompt=cfg.get("coach_prompt"),
    )
    reply = generate(system_prompt, _format_history(history, message))

    # Persist both messages, bump conversation timestamp.
    with get_conn() as conn:
        user_msg = conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s,'user',%s) RETURNING id",
            (conversation_id, message),
        ).fetchone()
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s,'assistant',%s)",
            (conversation_id, reply),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = now() WHERE id = %s", (conversation_id,)
        )
        conn.commit()
        user_msg_id = str(user_msg["id"])

    # Passive tagging (synchronous in demo mode). Never let a tagging failure
    # (e.g. a rate limit) break the user's reply — the message is already saved.
    tag = None
    if settings.synchronous_tagging:
        try:
            tag = tagging.tag_and_store(
                org_id=org_id,
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=user_msg_id,
                user_message=message,
                coach_reply=reply,
            )
        except Exception:  # noqa: BLE001
            tag = None

    return CoachResult(
        reply=reply, conversation_id=conversation_id, title=title, chunks=chunks, tag=tag
    )
