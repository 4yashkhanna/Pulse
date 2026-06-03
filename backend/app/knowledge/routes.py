"""Knowledge management routes — KPMG admin only.

The no-code ingestion endpoint: a consultant uploads files in the GUI and they are
parsed, chunked, embedded, and stored into that org's private knowledge base.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..auth.security import CurrentUser, require_kpmg_admin
from ..db import get_conn
from .ingest import ingest_document
from .parse import UnsupportedFormat

router = APIRouter(prefix="/orgs/{org_id}/knowledge", tags=["knowledge"])

ALLOWED = {".pdf", ".docx", ".pptx", ".txt", ".md", ".markdown"}


@router.get("")
def list_documents(org_id: str, _: CurrentUser = Depends(require_kpmg_admin)):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, filename, mime, status, n_chunks, error, created_at
            FROM knowledge_documents WHERE org_id = %s ORDER BY created_at DESC
            """,
            (org_id,),
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


@router.post("/upload")
async def upload(
    org_id: str,
    files: list[UploadFile] = File(...),
    user: CurrentUser = Depends(require_kpmg_admin),
):
    results = []
    for f in files:
        name = f.filename or "upload"
        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in ALLOWED:
            results.append({"filename": name, "status": "error", "error": f"Unsupported type {ext}"})
            continue
        data = await f.read()
        try:
            res = ingest_document(
                org_id=org_id,
                filename=name,
                mime=f.content_type,
                data=data,
                uploaded_by=user.id,
            )
            res["filename"] = name
            results.append(res)
        except UnsupportedFormat as exc:
            results.append({"filename": name, "status": "error", "error": str(exc)})
    return {"results": results}


@router.delete("/{document_id}")
def delete_document(org_id: str, document_id: str, _: CurrentUser = Depends(require_kpmg_admin)):
    with get_conn() as conn:
        r = conn.execute(
            "DELETE FROM knowledge_documents WHERE id = %s AND org_id = %s RETURNING id",
            (document_id, org_id),
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return {"deleted": document_id}
