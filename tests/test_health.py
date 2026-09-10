import pytest
from httpx import ASGITransport, AsyncClient

from labboard.app import create_app
from labboard.config import Settings


def test_jwt_secret_is_generated_and_persisted(tmp_path):
    secret_file = tmp_path / "secrets" / "jwt"
    settings = Settings(
        jwt_secret="",
        admin_password="a" * 12,
        jwt_secret_file=secret_file,
    )

    generated = settings.resolve_jwt_secret()

    assert len(generated) >= 32
    assert secret_file.read_text(encoding="ascii").strip() == generated
    assert Settings(jwt_secret="", admin_password="a" * 12, jwt_secret_file=secret_file).resolve_jwt_secret() == generated


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
