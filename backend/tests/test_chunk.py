"""Chunker: paragraph packing, long-paragraph splitting, overlap, empty input."""
from app.knowledge.chunk import MAX_CHARS, chunk_text


def test_empty_input_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("\n\n\n") == []


def test_short_text_is_one_chunk():
    assert chunk_text("Hello world.") == ["Hello world."]


def test_paragraphs_pack_into_chunks_under_limit():
    paras = [f"Paragraph {i} " + "x" * 200 for i in range(10)]
    chunks = chunk_text("\n\n".join(paras))
    assert len(chunks) > 1
    assert all(len(c) <= MAX_CHARS + 10 for c in chunks)


def test_long_paragraph_is_hard_split():
    text = "y" * (MAX_CHARS * 3)
    chunks = chunk_text(text)
    assert len(chunks) >= 3
    assert all(len(c) <= MAX_CHARS for c in chunks)


def test_collapses_excess_blank_lines():
    chunks = chunk_text("a\n\n\n\n\nb")
    assert chunks == ["a\n\nb"]
