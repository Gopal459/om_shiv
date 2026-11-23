import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_check_returns_ok():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "postgres" in data["components"]
    assert "redis" in data["components"]
