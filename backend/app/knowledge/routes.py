"""Org-level knowledge routes — KPMG admin only (scope = 'org')."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..auth.security import CurrentUser, require_kpmg_admin
from . import ingest

router = APIRouter(prefix="/orgs/{org_id}/knowledge", tags=["knowledge"])

ALLOWED = {".pdf", ".docx", ".pptx", ".txt", ".md", ".markdown"}


def _ext_ok(name: str) -> bool:
    return ("." + name.rsplit(".", 1)[-1].lower() if "." in name else "") in ALLOWED


@router.get("")
def list_documents(org_id: str, _: CurrentUser = Depends(require_kpmg_admin)):
    return ingest.list_documents(org_id, "org", org_id)


@router.post("/upload")
async def upload(
    org_id: str,
    files: list[UploadFile] = File(...),
    user: CurrentUser = Depends(require_kpmg_admin),
):
    payloads = []
    for f in files:
        name = f.filename or "upload"
        if not _ext_ok(name):
            payloads.append((name, f.content_type, None))
            continue
        payloads.append((name, f.content_type, await f.read()))
    results = []
    for name, mime, data in payloads:
        if data is None:
            results.append({"filename": name, "status": "error", "error": "Unsupported type"})
        else:
            results.extend(
                ingest.ingest_files(
                    org_id=org_id, scope="org", scope_id=org_id, uploaded_by=user.id,
                    files=[(name, mime, data)],
                )
            )
    return {"results": results}


@router.delete("/{document_id}")
def delete_document(org_id: str, document_id: str, _: CurrentUser = Depends(require_kpmg_admin)):
    if not ingest.delete_document(org_id, "org", org_id, document_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return {"deleted": document_id}
