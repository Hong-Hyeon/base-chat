import pytest
import asyncio

from app.services.gpt_embedding_service import GPTEmbeddingService


class DummyEmbeddingObject:
    def __init__(self, embedding):
        self.embedding = embedding


class DummyResponse:
    def __init__(self, embedding):
        self.data = [DummyEmbeddingObject(embedding)]


class DummyAsyncClient:
    class embeddings:
        @staticmethod
        async def create(model: str, input: str):
            # Return a small fixed vector for predictability
            return DummyResponse([0.1, 0.2, 0.3])


@pytest.mark.asyncio
async def test_gpt_embedding_service_create_embedding(monkeypatch):
    service = GPTEmbeddingService()

    # Patch client with dummy async client
    service.client = DummyAsyncClient()

    vector = await service.create_embedding("hello")

    assert isinstance(vector, list)
    assert vector == [0.1, 0.2, 0.3]
