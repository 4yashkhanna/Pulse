"""Retrieve relevant knowledge for a query, merging org + team + personal layers."""
from __future__ import annotations

from dataclasses import dataclass

from ..db import get_conn, to_pgvector
from .embed import embed_query


@dataclass
class Chunk:
    content: str
    source: str | None
    scope: str
    similarity: float


def retrieve(
    query: str,
    *,
    org_id: str,
    team_id: str | None = None,
    project_id: str | None = None,
    folder_ids: list[str] | None = None,
    k: int = 6,
) -> list[Chunk]:
    """Embed the query and return top-k similar chunks: org-general + the caller's
    team-general + the active project's knowledge + any folders imported into that
    project that the caller has access to (folder_ids)."""
    vec = embed_query(query)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM match_chunks(%s, %s, %s, %s, %s::vector, %s)",
            (org_id, team_id, project_id, folder_ids or [], to_pgvector(vec), k),
        ).fetchall()
    return [
        Chunk(content=r["content"], source=r["source"], scope=r["scope"], similarity=float(r["similarity"]))
        for r in rows
    ]
