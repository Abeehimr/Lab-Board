import pytest
from httpx import ASGITransport, AsyncClient

from labboard.app import create_app
from labboard.config import Settings


@pytest.mark.asyncio
async def test_health(tmp_path):
    settings = Settings(
        jwt_secret="a" * 32,
        admin_password="a" * 12,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}",
        upload_dir=tmp_path / "uploads",
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
            response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
