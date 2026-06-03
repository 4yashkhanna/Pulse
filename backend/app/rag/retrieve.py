"""Retrieve the most relevant KPMG knowledge chunks for a query."""
from __future__ import annotations

from dataclasses import dataclass

from ..db import get_conn, to_pgvector
from .embed import embed_query


@dataclass
class Chunk:
    content: str
    framework: str | None
    pillar: str | None
    phase: str | None
    industry: str | None
    similarity: float


def retrieve(query: str, *, industry: str | None = None, k: int = 6) -> list[Chunk]:
    """Embed the query and return top-k similar active chunks via match_chunks()."""
    vec = embed_query(query)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM match_chunks(%s::vector, %s, %s)",
            (to_pgvector(vec), k, industry),
        ).fetchall()
    return [
        Chunk(
            content=r["content"],
            framework=r["framework"],
            pillar=r["pillar"],
            phase=r["phase"],
            industry=r["industry"],
            similarity=float(r["similarity"]),
        )
        for r in rows
    ]
