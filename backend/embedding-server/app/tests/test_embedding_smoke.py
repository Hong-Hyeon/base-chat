import io
import pytest

from app.services.document_parser_service import DocumentParserService
from app.utils.chunking import TextChunker
from app.services.gpt_embedding_service import GPTEmbeddingService


@pytest.mark.asyncio
async def test_embedding_smoke_txt_html_json(monkeypatch, tmp_path):
    parser = DocumentParserService(ocr_enabled=False)
    chunker = TextChunker(max_chars=500, overlap_chars=50)

    # Prepare three simple files
    p_txt = tmp_path / "a.txt"
    p_txt.write_text("Hello World from TXT\n" * 10)

    p_html = tmp_path / "b.html"
    p_html.write_text("<html><body><p>Hello HTML</p></body></html>")

    p_json = tmp_path / "c.json"
    p_json.write_text('{"greeting": "Hello JSON"}')

    # Stub embedding service to avoid external API
    async def fake_create_embedding(self, text: str):  # type: ignore[override]
        # return small deterministic vector
        return [float(len(text) % 5), 0.5]

    monkeypatch.setattr(GPTEmbeddingService, "create_embedding", fake_create_embedding, raising=True)

    svc = GPTEmbeddingService()

    for path in [p_txt, p_html, p_json]:
        docs = parser.parse_file(str(path))
        chunks = chunker.chunk_documents(docs)
        assert len(chunks) >= 1
        # Create embeddings for first two chunks (if available)
        for chunk in chunks[:2]:
            emb = await svc.create_embedding(chunk["content"])  # type: ignore
            assert isinstance(emb, list) and len(emb) == 2


