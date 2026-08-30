import httpx
import pytest

from app.main import app

pytestmark = pytest.mark.anyio


async def test_root_returns_ok() -> None:
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "OK"}
