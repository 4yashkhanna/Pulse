"""Projects — personal (owner_kind='user') and team (owner_kind='team').

A project bundles its own knowledge and the conversations held inside it, like a Claude
Project. Personal projects belong to one user. Team projects are shared with a team;
only the manager can edit them, members can use them.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from ..auth.security import CurrentUser, get_current_user
from ..db import get_conn
from ..knowledge import ingest

router = APIRouter(prefix="/projects", tags=["projects"])

ALLOWED = {".pdf", ".docx", ".pptx", ".txt", ".md", ".markdown"}


def require_org_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organization users only")
    return user


class ProjectCreate(BaseModel):
    name: str


def _access(user: CurrentUser, project: dict) -> tuple[bool, bool]:
    """Return (can_view, can_edit) for this user on a project row."""
    if project["org_id"] != user.org_id:
        return False, False
    if project["owner_kind"] == "user":
        own = project["owner_id"] == user.id
        return own, own
    # team project
    same_team = user.team_id is not None and project["owner_id"] == user.team_id
    return same_team, same_team and user.role == "manager"


def _load(project_id: str) -> dict:
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM projects WHERE id = %s", (project_id,)).fetchone()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return {k: (str(v) if k.endswith("_id") or k == "id" else v) for k, v in r.items()}


async def _read(files: list[UploadFile]) -> list[tuple[str, str | None, bytes]]:
    out = []
    for f in files:
        name = f.filename or "upload"
        if ("." + name.rsplit(".", 1)[-1].lower() if "." in name else "") not in ALLOWED:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {name}")
        out.append((name, f.content_type, await f.read()))
    return out


@router.get("")
def list_projects(user: CurrentUser = Depends(require_org_user)):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT p.*, (SELECT COUNT(*) FROM knowledge_documents d WHERE d.project_id = p.id) AS n_docs
            FROM projects p
            WHERE p.org_id = %s
              AND ( (p.owner_kind='user' AND p.owner_id=%s)
                 OR (p.owner_kind='team' AND p.owner_id=%s) )
            ORDER BY p.owner_kind, p.created_at DESC
            """,
            (user.org_id, user.id, user.team_id),
        ).fetchall()
    out = []
    for r in rows:
        _, can_edit = _access(user, {**r, "org_id": str(r["org_id"]), "owner_id": str(r["owner_id"])})
        out.append(
            {
                "id": str(r["id"]),
                "name": r["name"],
                "kind": r["owner_kind"],
                "n_docs": int(r["n_docs"]),
                "can_edit": can_edit,
            }
        )
    return out


@router.post("", status_code=201)
def create_project(body: ProjectCreate, user: CurrentUser = Depends(require_org_user)):
    """Projects are personal — each belongs to the user who creates it."""
    with get_conn() as conn:
        r = conn.execute(
            "INSERT INTO projects (org_id, name, owner_kind, owner_id, created_by) "
            "VALUES (%s,%s,'user',%s,%s) RETURNING id",
            (user.org_id, body.name.strip() or "Untitled project", user.id, user.id),
        ).fetchone()
        conn.commit()
    return {"id": str(r["id"]), "name": body.name, "kind": "user", "can_edit": True, "n_docs": 0}


# --------------------------------------------------------------------------- #
# Importing team knowledge folders into a project
# --------------------------------------------------------------------------- #
@router.get("/{project_id}/folders")
def project_folders(project_id: str, user: CurrentUser = Depends(require_org_user)):
    """Folders imported into this project + the team folders the user could import
    (granted access, not yet imported)."""
    project = _load(project_id)
    _, can_edit = _access(user, project)
    if not can_edit:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this project")
    with get_conn() as conn:
        imported = conn.execute(
            """
            SELECT f.id, f.name, (SELECT COUNT(*) FROM knowledge_documents d WHERE d.folder_id=f.id) AS n_docs
            FROM project_folder_imports pfi JOIN knowledge_folders f ON f.id = pfi.folder_id
            WHERE pfi.project_id = %s ORDER BY f.name
            """,
            (project_id,),
        ).fetchall()
        # Granted folders not yet imported into this project.
        available = conn.execute(
            """
            SELECT f.id, f.name, (SELECT COUNT(*) FROM knowledge_documents d WHERE d.folder_id=f.id) AS n_docs
            FROM knowledge_folders f
            JOIN folder_access a ON a.folder_id = f.id AND a.user_id = %s AND a.status = 'granted'
            WHERE f.team_id = %s
              AND f.id NOT IN (SELECT folder_id FROM project_folder_imports WHERE project_id = %s)
            ORDER BY f.name
            """,
            (user.id, user.team_id, project_id),
        ).fetchall()
    fmt = lambda r: {"id": str(r["id"]), "name": r["name"], "n_docs": int(r["n_docs"])}
    return {"imported": [fmt(r) for r in imported], "available": [fmt(r) for r in available]}


def _has_folder_access(conn, folder_id: str, user: CurrentUser) -> bool:
    r = conn.execute(
        "SELECT 1 FROM folder_access WHERE folder_id=%s AND user_id=%s AND status='granted'",
        (folder_id, user.id),
    ).fetchone()
    return bool(r)


@router.post("/{project_id}/folders/{folder_id}")
def import_folder(project_id: str, folder_id: str, user: CurrentUser = Depends(require_org_user)):
    project = _load(project_id)
    _, can_edit = _access(user, project)
    if not can_edit:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your project")
    with get_conn() as conn:
        if not _has_folder_access(conn, folder_id, user):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have access to that folder")
        conn.execute(
            "INSERT INTO project_folder_imports (project_id, folder_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (project_id, folder_id),
        )
        conn.commit()
    return {"imported": folder_id}


@router.delete("/{project_id}/folders/{folder_id}")
def unimport_folder(project_id: str, folder_id: str, user: CurrentUser = Depends(require_org_user)):
    project = _load(project_id)
    _, can_edit = _access(user, project)
    if not can_edit:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your project")
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM project_folder_imports WHERE project_id=%s AND folder_id=%s", (project_id, folder_id)
        )
        conn.commit()
    return {"removed": folder_id}


@router.delete("/{project_id}")
def delete_project(project_id: str, user: CurrentUser = Depends(require_org_user)):
    project = _load(project_id)
    _, can_edit = _access(user, project)
    if not can_edit:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot delete this project")
    with get_conn() as conn:
        conn.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        conn.commit()
    return {"deleted": project_id}


@router.get("/{project_id}/knowledge")
def list_knowledge(project_id: str, user: CurrentUser = Depends(require_org_user)):
    can_view, _ = _access(user, _load(project_id))
    if not can_view:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this project")
    return ingest.list_project_documents(project_id)


@router.post("/{project_id}/knowledge/upload")
async def upload_knowledge(
    project_id: str, files: list[UploadFile] = File(...), user: CurrentUser = Depends(require_org_user)
):
    project = _load(project_id)
    _, can_edit = _access(user, project)
    if not can_edit:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot add files to this project")
    data = await _read(files)
    return {
        "results": ingest.ingest_files(
            org_id=user.org_id,  # type: ignore[arg-type]
            scope=project["owner_kind"],
            scope_id=project["owner_id"],
            uploaded_by=user.id,
            files=data,
            project_id=project_id,
        )
    }


@router.delete("/{project_id}/knowledge/{document_id}")
def delete_knowledge(project_id: str, document_id: str, user: CurrentUser = Depends(require_org_user)):
    _, can_edit = _access(user, _load(project_id))
    if not can_edit:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot remove files from this project")
    if not ingest.delete_project_document(project_id, document_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return {"deleted": document_id}
