"""Org-scoped ingestion: parse → chunk → embed → store, tracked per document.

Invoked from the Admin Portal upload endpoint, so a KPMG consultant never touches
a terminal — they drop files into the GUI and this runs server-side.
"""
from __future__ import annotations

from ..db import get_conn, to_pgvector
from ..rag.embed import embed_documents
from .chunk import chunk_text
from .parse import extract_text


def ingest_document(
    *, org_id: str, filename: str, mime: str | None, data: bytes, uploaded_by: str | None
) -> dict:
    """Process one uploaded file. Returns {document_id, n_chunks, status}."""
    with get_conn() as conn:
        doc = conn.execute(
            """
            INSERT INTO knowledge_documents (org_id, filename, mime, status, uploaded_by)
            VALUES (%s,%s,%s,'processing',%s) RETURNING id
            """,
            (org_id, filename, mime, uploaded_by),
        ).fetchone()
        conn.commit()
        document_id = str(doc["id"])

    try:
        text = extract_text(filename, data)
        chunks = chunk_text(text)
        if not chunks:
            _mark(document_id, "error", 0, "No extractable text found")
            return {"document_id": document_id, "n_chunks": 0, "status": "error"}

        embeddings = embed_documents(chunks)
        with get_conn() as conn:
            with conn.cursor() as cur:
                for idx, (content, emb) in enumerate(zip(chunks, embeddings)):
                    cur.execute(
                        """
                        INSERT INTO knowledge_chunks
                            (org_id, document_id, content, source, chunk_index, embedding)
                        VALUES (%s,%s,%s,%s,%s,%s::vector)
                        """,
                        (org_id, document_id, content, filename, idx, to_pgvector(emb)),
                    )
            conn.commit()
        _mark(document_id, "ready", len(chunks), None)
        return {"document_id": document_id, "n_chunks": len(chunks), "status": "ready"}
    except Exception as exc:  # noqa: BLE001 — surface the error to the UI
        _mark(document_id, "error", 0, str(exc)[:500])
        return {"document_id": document_id, "n_chunks": 0, "status": "error", "error": str(exc)}


def _mark(document_id: str, status: str, n_chunks: int, error: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE knowledge_documents SET status=%s, n_chunks=%s, error=%s WHERE id=%s",
            (status, n_chunks, error, document_id),
        )
        conn.commit()
