from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def test_app() -> FastAPI:
    from app.modules.project.get_fastapi_server import get_server

    server = get_server()
    return server._application


@pytest.fixture
async def test_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    from app.modules.db.postgres.clients import pg_clients

    test_app.dependency_overrides[pg_clients.project_client.get_dbsession_depends] = lambda: None

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


@pytest.fixture
def api_key_headers() -> dict[str, str]:
    from settings.settings import settings

    return {"X-API-Key": settings.project.credentials.API_KEY.get_secret_value()}
