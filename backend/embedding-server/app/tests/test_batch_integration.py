import pytest
import httpx
import uuid


@pytest.mark.asyncio
async def test_batch_embed_and_status():
    docs = [
        {"id": str(uuid.uuid4()), "content": f"batch doc {i}", "metadata": {"g": "b"}}
        for i in range(5)
    ]

    async with httpx.AsyncClient(base_url="http://localhost:8003", timeout=30.0) as client:
        r = await client.post("/batch/embed", json={"documents": docs})
        assert r.status_code == 200
        data = r.json()
        job_id = data.get("job_id")
        assert job_id

        # Poll job status a few times
        for _ in range(60):
            s = await client.get(f"/batch/status/{job_id}")
            assert s.status_code == 200
            info = s.json()
            if info.get("status") in {"completed", "FAILURE"}:
                break
            # wait a bit for worker to process
            import asyncio
            await asyncio.sleep(1)
        assert info.get("status") == "completed"
