import pytest
import httpx


@pytest.mark.asyncio
async def test_rag_search_via_main_backend():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        # call rag health to ensure client initialized
        h = await client.get("/rag/health")
        assert h.status_code == 200

        # insert a document via main-backend RAG embed endpoint (internally calls embedding-server)
        r = await client.post("/rag/embed", json={"text": "integration test doc", "metadata": {"src": "mb-test"}})
        assert r.status_code == 200

        # search through main-backend RAG endpoint
        s = await client.post("/rag/search", json={
            "query": "integration test",
            "top_k": 3,
            "similarity_threshold": 0.1
        })
        assert s.status_code == 200
        data = s.json()
        assert "results" in data
