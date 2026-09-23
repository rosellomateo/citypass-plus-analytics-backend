import httpx
import pytest

from app.core.config import CorsSettings
from app.main import app, create_app

pytestmark = pytest.mark.anyio


async def test_root_returns_ok() -> None:
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "OK"}


async def test_health_returns_ok() -> None:
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_cors_allows_configured_origin() -> None:
    allowed_origin = "http://localhost:5173"
    cors_app = create_app(CorsSettings(allowed_origins=(allowed_origin,)))
    transport = httpx.ASGITransport(app=cors_app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/analytics/reclamos",
            headers={
                "Origin": allowed_origin,
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == allowed_origin
    assert "GET" in response.headers["access-control-allow-methods"]


async def test_cors_does_not_allow_unconfigured_origin() -> None:
    cors_app = create_app(CorsSettings(allowed_origins=("http://localhost:5173",)))
    transport = httpx.ASGITransport(app=cors_app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/analytics/reclamos",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert "access-control-allow-origin" not in response.headers
