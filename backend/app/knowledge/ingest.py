"""Scoped knowledge ingestion: parse → chunk → embed → store, tracked per document.

A document belongs to a scope: 'org' (KPMG admin, whole org), 'team' (manager, a team),
or 'user' (personal/project knowledge). Retrieval merges all three for the caller.
"""
from __future__ import annotations

from ..db import get_conn, to_pgvector
from ..rag.embed import embed_documents
from .chunk import chunk_text
from .parse import extract_text


def ingest_document(
    *,
    org_id: str,
    scope: str,
    scope_id: str,
    filename: str,
    mime: str | None,
    data: bytes,
    uploaded_by: str | None,
    project_id: str | None = None,
    folder_id: str | None = None,
) -> dict:
    """Process one uploaded file into the given scope (project or folder optional)."""
    with get_conn() as conn:
        doc = conn.execute(
            """
            INSERT INTO knowledge_documents (org_id, scope, scope_id, project_id, folder_id, filename, mime, status, uploaded_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'processing',%s) RETURNING id
            """,
            (org_id, scope, scope_id, project_id, folder_id, filename, mime, uploaded_by),
        ).fetchone()
        conn.commit()
        document_id = str(doc["id"])

    try:
        text = extract_text(filename, data)
        chunks = chunk_text(text)
        if not chunks:
            _mark(document_id, "error", 0, "No extractable text found")
            return {"document_id": document_id, "n_chunks": 0, "status": "error", "filename": filename}

        embeddings = embed_documents(chunks)
        with get_conn() as conn:
            with conn.cursor() as cur:
                for idx, (content, emb) in enumerate(zip(chunks, embeddings)):
                    cur.execute(
                        """
                        INSERT INTO knowledge_chunks
                            (org_id, document_id, scope, scope_id, project_id, folder_id, content, source, chunk_index, embedding)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)
                        """,
                        (org_id, document_id, scope, scope_id, project_id, folder_id, content, filename, idx, to_pgvector(emb)),
                    )
            conn.commit()
        _mark(document_id, "ready", len(chunks), None)
        return {"document_id": document_id, "n_chunks": len(chunks), "status": "ready", "filename": filename}
    except Exception as exc:  # noqa: BLE001
        _mark(document_id, "error", 0, str(exc)[:500])
        return {"document_id": document_id, "n_chunks": 0, "status": "error", "error": str(exc), "filename": filename}


def ingest_files(
    *,
    org_id: str,
    scope: str,
    scope_id: str,
    uploaded_by: str | None,
    files: list[tuple[str, str | None, bytes]],
    project_id: str | None = None,
    folder_id: str | None = None,
) -> list[dict]:
    """files: list of (filename, mime, data). Returns one result per file."""
    return [
        ingest_document(
            org_id=org_id, scope=scope, scope_id=scope_id, project_id=project_id, folder_id=folder_id,
            filename=name, mime=mime, data=data, uploaded_by=uploaded_by,
        )
        for name, mime, data in files
    ]


def list_folder_documents(folder_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, filename, status, n_chunks, error, created_at FROM knowledge_documents "
            "WHERE folder_id = %s ORDER BY created_at DESC",
            (folder_id,),
        ).fetchall()
    return _rows_to_docs(rows)


def delete_folder_document(folder_id: str, document_id: str) -> bool:
    with get_conn() as conn:
        r = conn.execute(
            "DELETE FROM knowledge_documents WHERE id=%s AND folder_id=%s RETURNING id",
            (document_id, folder_id),
        ).fetchone()
        conn.commit()
    return bool(r)


def _rows_to_docs(rows) -> list[dict]:
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


def list_documents(org_id: str, scope: str, scope_id: str) -> list[dict]:
    """General-bucket documents (project_id IS NULL) for an org or team scope."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, filename, status, n_chunks, error, created_at
            FROM knowledge_documents
            WHERE org_id = %s AND scope = %s AND scope_id = %s AND project_id IS NULL
            ORDER BY created_at DESC
            """,
            (org_id, scope, scope_id),
        ).fetchall()
    return _rows_to_docs(rows)


def delete_document(org_id: str, scope: str, scope_id: str, document_id: str) -> bool:
    with get_conn() as conn:
        r = conn.execute(
            "DELETE FROM knowledge_documents WHERE id=%s AND org_id=%s AND scope=%s AND scope_id=%s "
            "AND project_id IS NULL RETURNING id",
            (document_id, org_id, scope, scope_id),
        ).fetchone()
        conn.commit()
    return bool(r)


def list_project_documents(project_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, filename, status, n_chunks, error, created_at
            FROM knowledge_documents WHERE project_id = %s ORDER BY created_at DESC
            """,
            (project_id,),
        ).fetchall()
    return _rows_to_docs(rows)


def delete_project_document(project_id: str, document_id: str) -> bool:
    with get_conn() as conn:
        r = conn.execute(
            "DELETE FROM knowledge_documents WHERE id=%s AND project_id=%s RETURNING id",
            (document_id, project_id),
        ).fetchone()
        conn.commit()
    return bool(r)


def _mark(document_id: str, status: str, n_chunks: int, error: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE knowledge_documents SET status=%s, n_chunks=%s, error=%s WHERE id=%s",
            (status, n_chunks, error, document_id),
        )
        conn.commit()
