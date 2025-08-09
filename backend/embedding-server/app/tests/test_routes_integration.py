import pytest
import httpx


@pytest.mark.asyncio
async def test_embed_and_search_flow():
    async with httpx.AsyncClient(base_url="http://localhost:8003", timeout=10.0) as client:
        # create embedding
        r = await client.post("/embed/", json={"text": "hello test", "metadata": {"source": "pytest"}})
        assert r.status_code == 200
        data = r.json()
        assert "document_id" in data

        # search with filter
        s = await client.post("/embed/search", json={
            "query": "hello",
            "top_k": 3,
            "similarity_threshold": 0.1,
            "filters": {"source": "pytest"}
        })
        assert s.status_code == 200
        sdata = s.json()
        assert isinstance(sdata.get("results", []), list)
