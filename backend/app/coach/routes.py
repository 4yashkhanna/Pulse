"""Chatbot routes — for org users (employee / manager). KPMG admins have no org."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from ..auth.security import CurrentUser, get_current_user
from ..db import get_conn
from ..llm import RateLimited
from . import chat as coach_chat

router = APIRouter(tags=["coach"])

# Image + PDF only (audio comes in a later pass). 15 MB per file cap.
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif", "application/pdf"}
MAX_FILE_BYTES = 15 * 1024 * 1024


def require_org_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Coach is for organization users")
    return user


def _owns(conn, conversation_id: str, user_id: str) -> bool:
    r = conn.execute(
        "SELECT 1 FROM conversations WHERE id = %s AND user_id = %s",
        (conversation_id, user_id),
    ).fetchone()
    return bool(r)


@router.post("/chat")
async def chat(
    message: str = Form(""),
    conversation_id: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
    user: CurrentUser = Depends(require_org_user),
):
    if conversation_id:
        with get_conn() as conn:
            if not _owns(conn, conversation_id, user.id):
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    attachments: list[tuple[str, bytes, str]] = []
    for f in files:
        mime = f.content_type or ""
        if mime not in ALLOWED_MIME:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {mime or f.filename}")
        data = await f.read()
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{f.filename} exceeds 15 MB")
        attachments.append((mime, data, f.filename or "file"))

    if not message.strip() and not attachments:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Send a message or attach a file")

    try:
        result = coach_chat.run_turn(
            message=message,
            org_id=user.org_id,  # type: ignore[arg-type]
            user_id=user.id,
            conversation_id=conversation_id,
            attachments=attachments,
        )
    except RateLimited:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "The coach is rate-limited on the free Gemini tier. Wait a few seconds and try again.",
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
