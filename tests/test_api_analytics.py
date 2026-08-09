import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_get_analytics_summary(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/api/v1/analytics/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()
    # New contract groups totals under a 'totals' object
    assert "totals" in body
    assert "documents" in body["totals"]
    assert "storage_bytes" in body["totals"]

@pytest.mark.anyio
async def test_get_processing_queue(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/api/v1/analytics/processing", headers=headers)
    assert response.status_code == 200
    body = response.json()
    # New contract exposes status_counts and processed_total
    assert "status_counts" in body
    assert "processed_total" in body
