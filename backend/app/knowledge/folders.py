"""Knowledge folders — manager-curated, shareable RAG sets for a team.

- Manager: create a folder, upload docs, grant/revoke access per team member, see requests.
- Member: see team folders + their access status; request access; (importing a granted
  folder into a project lives in the projects router).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from ..auth.security import CurrentUser, get_current_user
from ..db import get_conn
from . import ingest

router = APIRouter(prefix="/folders", tags=["folders"])

ALLOWED = {".pdf", ".docx", ".pptx", ".txt", ".md", ".markdown"}


def require_org_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organization users only")
    return user


def require_manager(user: CurrentUser = Depends(require_org_user)) -> CurrentUser:
    if user.role != "manager" or not user.team_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Team manager only")
    return user


class FolderCreate(BaseModel):
    name: str


class AccessChange(BaseModel):
    user_id: str
    action: str  # grant | revoke


async def _read(files: list[UploadFile]) -> list[tuple[str, str | None, bytes]]:
    out = []
    for f in files:
        name = f.filename or "upload"
        if ("." + name.rsplit(".", 1)[-1].lower() if "." in name else "") not in ALLOWED:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {name}")
        out.append((name, f.content_type, await f.read()))
    return out


def _folder_team(folder_id: str) -> dict:
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM knowledge_folders WHERE id = %s", (folder_id,)).fetchone()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found")
    return {"id": str(r["id"]), "org_id": str(r["org_id"]), "team_id": str(r["team_id"]), "name": r["name"]}


def _manages(folder: dict, user: CurrentUser) -> bool:
    return user.role == "manager" and folder["team_id"] == user.team_id


# --------------------------------------------------------------------------- #
@router.get("")
def list_folders(user: CurrentUser = Depends(require_org_user)):
    """Folders for the caller's team, with doc counts and the caller's access status."""
    if not user.team_id:
        return []
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT f.id, f.name,
                   (SELECT COUNT(*) FROM knowledge_documents d WHERE d.folder_id = f.id) AS n_docs,
                   (SELECT COUNT(*) FROM folder_access a WHERE a.folder_id = f.id AND a.status='granted') AS n_granted,
                   (SELECT COUNT(*) FROM folder_access a WHERE a.folder_id = f.id AND a.status='requested') AS n_requests,
                   (SELECT status FROM folder_access a WHERE a.folder_id = f.id AND a.user_id = %s) AS my_status
            FROM knowledge_folders f
            WHERE f.team_id = %s ORDER BY f.created_at DESC
            """,
            (user.id, user.team_id),
        ).fetchall()
    is_mgr = user.role == "manager"
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "n_docs": int(r["n_docs"]),
            "n_granted": int(r["n_granted"]) if is_mgr else None,
            "n_requests": int(r["n_requests"]) if is_mgr else None,
            "my_status": ("granted" if is_mgr else r["my_status"]),  # managers implicitly have access
            "can_edit": is_mgr,
        }
        for r in rows
    ]


@router.post("", status_code=201)
def create_folder(body: FolderCreate, user: CurrentUser = Depends(require_manager)):
    with get_conn() as conn:
        r = conn.execute(
            "INSERT INTO knowledge_folders (org_id, team_id, name, created_by) VALUES (%s,%s,%s,%s) RETURNING id",
            (user.org_id, user.team_id, body.name.strip() or "Untitled folder", user.id),
        ).fetchone()
        conn.commit()
    return {"id": str(r["id"]), "name": body.name, "n_docs": 0, "my_status": "granted", "can_edit": True}


@router.delete("/{folder_id}")
def delete_folder(folder_id: str, user: CurrentUser = Depends(require_org_user)):
    folder = _folder_team(folder_id)
    if not _manages(folder, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the team manager can delete this folder")
    with get_conn() as conn:
        conn.execute("DELETE FROM knowledge_folders WHERE id = %s", (folder_id,))
        conn.commit()
    return {"deleted": folder_id}


@router.get("/{folder_id}/knowledge")
def list_knowledge(folder_id: str, user: CurrentUser = Depends(require_org_user)):
    folder = _folder_team(folder_id)
    if folder["team_id"] != user.team_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your team's folder")
    return ingest.list_folder_documents(folder_id)


@router.post("/{folder_id}/knowledge/upload")
async def upload_knowledge(folder_id: str, files: list[UploadFile] = File(...), user: CurrentUser = Depends(require_org_user)):
    folder = _folder_team(folder_id)
    if not _manages(folder, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the team manager can add files")
    data = await _read(files)
    return {"results": ingest.ingest_files(
        org_id=user.org_id, scope="team", scope_id=user.team_id, uploaded_by=user.id, files=data, folder_id=folder_id,  # type: ignore[arg-type]
    )}


@router.delete("/{folder_id}/knowledge/{document_id}")
def delete_knowledge(folder_id: str, document_id: str, user: CurrentUser = Depends(require_org_user)):
    folder = _folder_team(folder_id)
    if not _manages(folder, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the team manager can remove files")
    if not ingest.delete_folder_document(folder_id, document_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return {"deleted": document_id}


# --------------------------------------------------------------------------- #
# Access management
# --------------------------------------------------------------------------- #
@router.get("/{folder_id}/access")
def access_list(folder_id: str, user: CurrentUser = Depends(require_org_user)):
    """Manager view: every team member and their access status to this folder."""
    folder = _folder_team(folder_id)
    if not _manages(folder, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Manager only")
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.name, u.role, a.status
            FROM users u
            LEFT JOIN folder_access a ON a.folder_id = %s AND a.user_id = u.id
            WHERE u.team_id = %s AND u.role <> 'manager'
            ORDER BY u.name
            """,
            (folder_id, user.team_id),
        ).fetchall()
    return [
        {"id": str(r["id"]), "name": r["name"], "status": r["status"] or "none"}
        for r in rows
    ]


@router.post("/{folder_id}/access")
def access_change(folder_id: str, body: AccessChange, user: CurrentUser = Depends(require_org_user)):
    folder = _folder_team(folder_id)
    if not _manages(folder, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Manager only")
    with get_conn() as conn:
        if body.action == "grant":
            conn.execute(
                """
                INSERT INTO folder_access (folder_id, user_id, status) VALUES (%s,%s,'granted')
                ON CONFLICT (folder_id, user_id) DO UPDATE SET status='granted'
                """,
                (folder_id, body.user_id),
            )
        elif body.action == "revoke":
            conn.execute(
                "DELETE FROM folder_access WHERE folder_id=%s AND user_id=%s", (folder_id, body.user_id)
            )
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "action must be grant or revoke")
        conn.commit()
    return {"ok": True}


@router.post("/{folder_id}/request")
def request_access(folder_id: str, user: CurrentUser = Depends(require_org_user)):
    folder = _folder_team(folder_id)
    if folder["team_id"] != user.team_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your team's folder")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO folder_access (folder_id, user_id, status) VALUES (%s,%s,'requested')
            ON CONFLICT (folder_id, user_id) DO NOTHING
            """,
            (folder_id, user.id),
        )
        conn.commit()
    return {"status": "requested"}
