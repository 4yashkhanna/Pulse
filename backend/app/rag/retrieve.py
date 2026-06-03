"""Retrieve the most relevant knowledge chunks for a query, scoped to one org."""
from __future__ import annotations

from dataclasses import dataclass

from ..db import get_conn, to_pgvector
from .embed import embed_query


@dataclass
class Chunk:
    content: str
    source: str | None
    similarity: float


def retrieve(query: str, *, org_id: str, k: int = 6) -> list[Chunk]:
    """Embed the query and return top-k similar active chunks for this org."""
    vec = embed_query(query)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM match_chunks(%s, %s::vector, %s)",
            (org_id, to_pgvector(vec), k),
        ).fetchall()
    return [
        Chunk(content=r["content"], source=r["source"], similarity=float(r["similarity"]))
        for r in rows
    ]
