"""Team & personal knowledge — for org users (manager / employee), NOT KPMG admin.

- Personal ('user' scope): any org user manages their own project knowledge (like a Claude
  Project). A manager can also manage a specific team member's personal knowledge.
- Team ('team' scope): a manager manages knowledge shared with their whole team; members
  can view the list.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..auth.security import CurrentUser, get_current_user
from ..db import get_conn
from . import ingest

router = APIRouter(prefix="/knowledge", tags=["knowledge-scoped"])

ALLOWED = {".pdf", ".docx", ".pptx", ".txt", ".md", ".markdown"}


def require_org_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organization users only")
    return user


def _ext_ok(name: str) -> bool:
    return ("." + name.rsplit(".", 1)[-1].lower() if "." in name else "") in ALLOWED


async def _read(files: list[UploadFile]) -> list[tuple[str, str | None, bytes]]:
    out = []
    for f in files:
        name = f.filename or "upload"
        if not _ext_ok(name):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {name}")
        out.append((name, f.content_type, await f.read()))
    return out


def _member_or_403(manager: CurrentUser, member_id: str) -> None:
    if manager.role != "manager":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Managers only")
    with get_conn() as conn:
        r = conn.execute(
            "SELECT 1 FROM users WHERE id=%s AND org_id=%s AND team_id=%s",
            (member_id, manager.org_id, manager.team_id),
        ).fetchone()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not a member of your team")


# --------------------------------------------------------------------------- #
# Personal / project knowledge (own)
# --------------------------------------------------------------------------- #
@router.get("/me")
def my_docs(user: CurrentUser = Depends(require_org_user)):
    return ingest.list_documents(user.org_id, "user", user.id)  # type: ignore[arg-type]


@router.post("/me/upload")
async def upload_me(files: list[UploadFile] = File(...), user: CurrentUser = Depends(require_org_user)):
    data = await _read(files)
    return {"results": ingest.ingest_files(
        org_id=user.org_id, scope="user", scope_id=user.id, uploaded_by=user.id, files=data,  # type: ignore[arg-type]
    )}


@router.delete("/me/{document_id}")
def delete_me(document_id: str, user: CurrentUser = Depends(require_org_user)):
    if not ingest.delete_document(user.org_id, "user", user.id, document_id):  # type: ignore[arg-type]
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return {"deleted": document_id}


# --------------------------------------------------------------------------- #
# Team knowledge (manager manages; members may view)
# --------------------------------------------------------------------------- #
@router.get("/team")
def team_docs(user: CurrentUser = Depends(require_org_user)):
    if not user.team_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You are not on a team")
    return ingest.list_documents(user.org_id, "team", user.team_id)  # type: ignore[arg-type]


@router.post("/team/upload")
async def upload_team(files: list[UploadFile] = File(...), user: CurrentUser = Depends(require_org_user)):
    if user.role != "manager" or not user.team_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the team manager can add team knowledge")
    data = await _read(files)
    return {"results": ingest.ingest_files(
        org_id=user.org_id, scope="team", scope_id=user.team_id, uploaded_by=user.id, files=data,  # type: ignore[arg-type]
    )}


@router.delete("/team/{document_id}")
def delete_team(document_id: str, user: CurrentUser = Depends(require_org_user)):
    if user.role != "manager" or not user.team_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the team manager can remove team knowledge")
    if not ingest.delete_document(user.org_id, "team", user.team_id, document_id):  # type: ignore[arg-type]
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return {"deleted": document_id}


# --------------------------------------------------------------------------- #
# A manager managing a specific team member's personal knowledge
# --------------------------------------------------------------------------- #
@router.get("/member/{member_id}")
def member_docs(member_id: str, user: CurrentUser = Depends(require_org_user)):
    _member_or_403(user, member_id)
    return ingest.list_documents(user.org_id, "user", member_id)  # type: ignore[arg-type]


@router.post("/member/{member_id}/upload")
async def upload_member(member_id: str, files: list[UploadFile] = File(...), user: CurrentUser = Depends(require_org_user)):
    _member_or_403(user, member_id)
    data = await _read(files)
    return {"results": ingest.ingest_files(
        org_id=user.org_id, scope="user", scope_id=member_id, uploaded_by=user.id, files=data,  # type: ignore[arg-type]
    )}


@router.delete("/member/{member_id}/{document_id}")
def delete_member(member_id: str, document_id: str, user: CurrentUser = Depends(require_org_user)):
    _member_or_403(user, member_id)
    if not ingest.delete_document(user.org_id, "user", member_id, document_id):  # type: ignore[arg-type]
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return {"deleted": document_id}
