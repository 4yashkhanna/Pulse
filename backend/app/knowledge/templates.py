"""Knowledge templates — global, premade RAG sets per maturity stage or sector.

KPMG admins curate documents into templates (scope='template', org_id NULL). Applying a
template to an organization COPIES its ready documents — chunks and embeddings included,
so it's instant and costs no re-embedding — into that org's knowledge. The copies are
normal org documents (tagged with from_template_id) that can then be tweaked per-org.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from ..auth.security import CurrentUser, require_kpmg_admin
from ..db import get_conn
from . import ingest

router = APIRouter(
    prefix="/templates", tags=["templates"], dependencies=[Depends(require_kpmg_admin)]
)

ALLOWED = {".pdf", ".docx", ".pptx", ".txt", ".md", ".markdown"}

# Buckets that always exist (auto-seeded on first list).
DEFAULT_TEMPLATES = [
    ("stage", "stage-1", "Stage 1 · Initial Assessment"),
    ("stage", "stage-2", "Stage 2 · Foundation"),
    ("stage", "stage-3", "Stage 3 · Optimization"),
    ("stage", "stage-4", "Stage 4 · Optimized"),
    ("stage", "stage-5", "Stage 5 · Target Goal"),
    ("sector", "tech", "Technology"),
    ("sector", "fmcg", "FMCG & Consumer"),
    ("sector", "banking", "Banking & Financial Services"),
    ("sector", "healthcare", "Healthcare"),
    ("sector", "government", "Government & Public Sector"),
]


class SectorCreate(BaseModel):
    key: str
    name: str
    description: str = ""


def _ensure_defaults(conn) -> None:
    for kind, key, name in DEFAULT_TEMPLATES:
        conn.execute(
            "INSERT INTO knowledge_templates (kind, key, name) VALUES (%s,%s,%s) "
            "ON CONFLICT (kind, key) DO NOTHING",
            (kind, key, name),
        )
    conn.commit()


@router.get("")
def list_templates():
    with get_conn() as conn:
        _ensure_defaults(conn)
        rows = conn.execute(
            """
            SELECT t.*,
                   (SELECT COUNT(*) FROM knowledge_documents d
                     WHERE d.scope='template' AND d.scope_id = t.id) AS n_docs,
                   (SELECT COALESCE(SUM(d.n_chunks),0) FROM knowledge_documents d
                     WHERE d.scope='template' AND d.scope_id = t.id AND d.status='ready') AS n_chunks
            FROM knowledge_templates t
            ORDER BY t.kind, t.key
            """
        ).fetchall()
    return [
        {
            "id": str(r["id"]),
            "kind": r["kind"],
            "key": r["key"],
            "name": r["name"],
            "description": r["description"],
            "n_docs": int(r["n_docs"]),
            "n_chunks": int(r["n_chunks"]),
        }
        for r in rows
    ]


@router.post("/sectors", status_code=201)
def create_sector(body: SectorCreate):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT 1 FROM knowledge_templates WHERE kind='sector' AND key=%s", (body.key,)
        ).fetchone()
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "A sector with that key already exists")
        r = conn.execute(
            "INSERT INTO knowledge_templates (kind, key, name, description) "
            "VALUES ('sector',%s,%s,%s) RETURNING id",
            (body.key.strip().lower().replace(" ", "-"), body.name, body.description),
        ).fetchone()
        conn.commit()
    return {"id": str(r["id"]), "kind": "sector", "key": body.key, "name": body.name}


def _template(conn, template_id: str) -> dict:
    r = conn.execute("SELECT * FROM knowledge_templates WHERE id = %s", (template_id,)).fetchone()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    return r


# --------------------------------------------------------------------------- #
# Template documents
# --------------------------------------------------------------------------- #
@router.get("/{template_id}/knowledge")
def list_docs(template_id: str):
    with get_conn() as conn:
        _template(conn, template_id)
        rows = conn.execute(
            """
            SELECT id, filename, status, n_chunks, error, created_at
            FROM knowledge_documents WHERE scope='template' AND scope_id=%s
            ORDER BY created_at DESC
            """,
            (template_id,),
        ).fetchall()
    return [
        {
            "id": str(r["id"]),
            "filename": r["filename"],
            "status": r["status"],
            "n_chunks": r["n_chunks"],
            "error": r["error"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.post("/{template_id}/knowledge/upload")
async def upload_docs(
    template_id: str,
    files: list[UploadFile] = File(...),
    user: CurrentUser = Depends(require_kpmg_admin),
):
    with get_conn() as conn:
        _template(conn, template_id)
    payload: list[tuple[str, str | None, bytes]] = []
    for f in files:
        name = f.filename or "upload"
        if ("." + name.rsplit(".", 1)[-1].lower() if "." in name else "") not in ALLOWED:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {name}")
        payload.append((name, f.content_type, await f.read()))
    return {
        "results": ingest.ingest_files(
            org_id=None,  # type: ignore[arg-type] — templates are global
            scope="template",
            scope_id=template_id,
            uploaded_by=user.id,
            files=payload,
        )
    }


@router.delete("/{template_id}/knowledge/{document_id}")
def delete_doc(template_id: str, document_id: str):
    with get_conn() as conn:
        r = conn.execute(
            "DELETE FROM knowledge_documents WHERE id=%s AND scope='template' AND scope_id=%s RETURNING id",
            (document_id, template_id),
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return {"deleted": document_id}


# --------------------------------------------------------------------------- #
# Apply a template to an organization (copy docs + chunks; no re-embedding)
# --------------------------------------------------------------------------- #
@router.post("/{template_id}/apply/{org_id}")
def apply_to_org(template_id: str, org_id: str, user: CurrentUser = Depends(require_kpmg_admin)):
    with get_conn() as conn:
        tpl = _template(conn, template_id)
        org = conn.execute("SELECT 1 FROM organizations WHERE id=%s", (org_id,)).fetchone()
        if not org:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")

        docs = conn.execute(
            "SELECT * FROM knowledge_documents WHERE scope='template' AND scope_id=%s AND status='ready'",
            (template_id,),
        ).fetchall()

        copied, skipped = [], []
        for d in docs:
            # Skip if this org already has this doc from this template (re-apply = add new only).
            dup = conn.execute(
                "SELECT 1 FROM knowledge_documents WHERE org_id=%s AND from_template_id=%s AND filename=%s",
                (org_id, template_id, d["filename"]),
            ).fetchone()
            if dup:
                skipped.append(d["filename"])
                continue
            new_doc = conn.execute(
                """
                INSERT INTO knowledge_documents
                    (org_id, scope, scope_id, filename, mime, status, n_chunks, uploaded_by, from_template_id)
                VALUES (%s,'org',%s,%s,%s,'ready',%s,%s,%s) RETURNING id
                """,
                (org_id, org_id, d["filename"], d["mime"], d["n_chunks"], user.id, template_id),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO knowledge_chunks
                    (org_id, document_id, scope, scope_id, content, source, chunk_index, active, embedding)
                SELECT %s, %s, 'org', %s, content, source, chunk_index, active, embedding
                FROM knowledge_chunks WHERE document_id = %s
                """,
                (org_id, str(new_doc["id"]), org_id, str(d["id"])),
            )
            copied.append(d["filename"])
        conn.commit()

    return {"template": tpl["name"], "copied": copied, "skipped": skipped}
