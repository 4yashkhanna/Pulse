"""Chatbot routes — for org users (employee / manager). KPMG admins have no org."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth.security import CurrentUser, get_current_user
from ..db import get_conn
from . import chat as coach_chat

router = APIRouter(tags=["coach"])


def require_org_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Coach is for organization users")
    return user


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


def _owns(conn, conversation_id: str, user_id: str) -> bool:
    r = conn.execute(
        "SELECT 1 FROM conversations WHERE id = %s AND user_id = %s",
        (conversation_id, user_id),
    ).fetchone()
    return bool(r)


@router.post("/chat")
def chat(req: ChatRequest, user: CurrentUser = Depends(require_org_user)):
    if req.conversation_id:
        with get_conn() as conn:
            if not _owns(conn, req.conversation_id, user.id):
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    result = coach_chat.run_turn(
        message=req.message,
        org_id=user.org_id,  # type: ignore[arg-type]
        user_id=user.id,
        conversation_id=req.conversation_id,
    )
    return {
        "reply": result.reply,
        "conversation_id": result.conversation_id,
        "title": result.title,
        "retrieved": [
            {"source": c.source, "similarity": round(c.similarity, 3)} for c in result.chunks
        ],
        "tag": result.tag,
    }


@router.get("/conversations")
def list_conversations(q: str | None = None, user: CurrentUser = Depends(require_org_user)):
    """List the current user's conversations, optionally filtered by a search query
    that matches the title or any message content."""
    with get_conn() as conn:
        if q:
            rows = conn.execute(
                """
                SELECT DISTINCT c.id, c.title, c.updated_at
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                WHERE c.user_id = %s
                  AND (c.title ILIKE %s OR m.content ILIKE %s)
                ORDER BY c.updated_at DESC
                """,
                (user.id, f"%{q}%", f"%{q}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, updated_at FROM conversations WHERE user_id = %s ORDER BY updated_at DESC",
                (user.id,),
            ).fetchall()
    return [
        {"id": str(r["id"]), "title": r["title"], "updated_at": r["updated_at"].isoformat()}
        for r in rows
    ]


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, user: CurrentUser = Depends(require_org_user)):
    with get_conn() as conn:
        if not _owns(conn, conversation_id, user.id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at",
            (conversation_id,),
        ).fetchall()
    return {
        "id": conversation_id,
        "messages": [{"role": r["role"], "content": r["content"]} for r in rows],
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, user: CurrentUser = Depends(require_org_user)):
    with get_conn() as conn:
        if not _owns(conn, conversation_id, user.id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        conn.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
        conn.commit()
    return {"deleted": conversation_id}
