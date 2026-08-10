"""Split extracted text into overlapping chunks for embedding.

A simple, robust length-based splitter that prefers paragraph boundaries — good
enough for workshop notes, decks, and playbooks dropped in by a consultant.
"""
from __future__ import annotations

import re

MAX_CHARS = 1100
OVERLAP = 150


def chunk_text(text: str, *, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(para) > max_chars:
            # Flush buffer, then hard-split the long paragraph.
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(para), max_chars - overlap):
                chunks.append(para[i : i + max_chars])
            continue
        if len(buf) + len(para) + 2 <= max_chars:
            buf = f"{buf}\n\n{para}" if buf else para
        else:
            chunks.append(buf)
            # carry a little overlap for context continuity
            tail = buf[-overlap:] if overlap else ""
            buf = f"{tail}\n\n{para}".strip() if tail else para
    if buf:
        chunks.append(buf)
    return chunks
