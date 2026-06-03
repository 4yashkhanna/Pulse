"""Knowledge ingestion: chunk markdown files, embed, and upsert into pgvector.

This is the heart of the "online update" story: run this to add or refresh
knowledge and every user picks it up on their next message — no per-device sync.

Markdown convention (one block per framework/concept):

    ## Journey Map
    <!-- meta: framework=Journey Map; pillar=process; phase=empathy; industry=generic -->
    Body text...

Each `##` section becomes one chunk. The optional meta comment sets tags.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..db import get_conn, to_pgvector
from .embed import embed_documents

META_RE = re.compile(r"<!--\s*meta:(.*?)-->", re.DOTALL)
SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _parse_meta(block: str) -> dict[str, str]:
    m = META_RE.search(block)
    if not m:
        return {}
    out: dict[str, str] = {}
    for pair in m.group(1).split(";"):
        if "=" in pair:
            key, val = pair.split("=", 1)
            out[key.strip()] = val.strip()
    return out


def parse_markdown(path: Path) -> list[dict]:
    """Split a markdown file into one chunk per `## Heading` section."""
    text = path.read_text(encoding="utf-8")
    chunks: list[dict] = []
    matches = list(SECTION_RE.finditer(text))
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        meta = _parse_meta(body)
        clean_body = META_RE.sub("", body).strip()
        if not clean_body:
            continue
        chunks.append(
            {
                "content": f"{title}\n\n{clean_body}",
                "source": path.name,
                "framework": meta.get("framework", title),
                "pillar": meta.get("pillar"),
                "phase": meta.get("phase"),
                "industry": meta.get("industry", "generic"),
            }
        )
    return chunks


def ingest_paths(paths: list[Path], *, replace_source: bool = True) -> int:
    """Embed and upsert all chunks from the given markdown files.

    If replace_source, existing rows for each file are deleted first so re-running
    is idempotent (the realistic "update a framework" flow)."""
    all_chunks: list[dict] = []
    for p in paths:
        all_chunks.extend(parse_markdown(p))

    if not all_chunks:
        return 0

    embeddings = embed_documents([c["content"] for c in all_chunks])

    with get_conn() as conn:
        with conn.cursor() as cur:
            if replace_source:
                for source in {c["source"] for c in all_chunks}:
                    cur.execute("DELETE FROM knowledge_chunks WHERE source = %s", (source,))
            for chunk, emb in zip(all_chunks, embeddings):
                cur.execute(
                    """
                    INSERT INTO knowledge_chunks
                        (content, source, framework, pillar, phase, industry, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                    """,
                    (
                        chunk["content"],
                        chunk["source"],
                        chunk["framework"],
                        chunk["pillar"],
                        chunk["phase"],
                        chunk["industry"],
                        to_pgvector(emb),
                    ),
                )
        conn.commit()
    return len(all_chunks)
