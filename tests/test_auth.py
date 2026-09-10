import pytest
from httpx import ASGITransport, AsyncClient

from labboard.app import create_app
from labboard.config import Settings


@pytest.mark.asyncio
async def test_login_csrf_logout(tmp_path):
    settings = Settings(
        jwt_secret="b" * 32,
        admin_password="correct-horse-battery",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}",
        upload_dir=tmp_path / "uploads",
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
            denied = await client.post("/api/auth/login", json={"password": "wrong"})
            assert denied.status_code == 401
            logged_in = await client.post("/api/auth/login", json={"password": settings.admin_password})
            assert logged_in.status_code == 200
            csrf = client.cookies.get("labboard_csrf")
            assert csrf
            missing_csrf = await client.post("/api/auth/logout")
            assert missing_csrf.status_code == 403
            logged_out = await client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
            assert logged_out.status_code == 200
