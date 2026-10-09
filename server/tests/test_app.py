"""Integration tests for FastAPI endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from server.app import app, db_manager


@pytest.fixture(autouse=True)
async def setup_database():
    """Initializes database schema before tests."""
    await db_manager.initialize()


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["timezone"] == "America/Sao_Paulo"


@pytest.mark.asyncio
async def test_gateway_json_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "header": {
                "service": "userservice",
                "version": "36.1.4.9545",
                "rpcthing": "rpc-test-999",
            },
            "body": {
                "all_in_one_login": {
                    "cinta": "676d4d53-f0cb-41c6-8c27-4bb3c3c3c905",
                }
            },
        }
        res = await client.post("/gateway", json=payload)
        assert res.status_code == 200
        json_data = res.json()
        assert json_data["header"]["status"] == 200
        assert json_data["header"]["rpcthing"] == "rpc-test-999"
        assert "resp_login_of_some_type" in json_data["body"]
