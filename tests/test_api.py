import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from core.utils.security import create_signed_token

@pytest.mark.asyncio
async def test_health_check_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "humatron-bot-api"
    assert data["status"] in ["healthy", "degraded"]

@pytest.mark.asyncio
async def test_verify_token_endpoint():
    valid_token = create_signed_token(telegram_id=12345678, expires_in_seconds=600)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/auth/verify-token?token={valid_token}")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["telegram_id"] == 12345678

@pytest.mark.asyncio
async def test_verify_invalid_token_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/auth/verify-token?token=invalid.token.payload")
    assert response.status_code == 400
