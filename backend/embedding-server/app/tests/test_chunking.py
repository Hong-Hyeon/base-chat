from app.utils.chunking import TextChunker


def test_chunker_basic_split():
    text = ("Para1\n" * 200) + "\n\n" + ("Para2\n" * 200)
    chunker = TextChunker(max_chars=1000, overlap_chars=100)
    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 2
    # Overlap check: next chunk should start with tail of previous
    if len(chunks) >= 2:
        assert chunks[1].startswith(chunks[0][-100:])


def test_chunk_documents_carries_metadata():
    docs = [
        {"content": "A" * 1200, "metadata": {"k": "v"}, "source": "s.txt", "mime_type": "text/plain"}
    ]
    chunker = TextChunker(max_chars=800, overlap_chars=100)
    out = chunker.chunk_documents(docs)
    assert len(out) >= 2
    for i, d in enumerate(out):
        assert d["metadata"]["chunk_index"] == i
        assert d["metadata"]["num_chunks"] == len(out)
        assert d["source"] == "s.txt"


