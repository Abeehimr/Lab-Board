import pytest
from httpx import ASGITransport, AsyncClient

from labboard.app import create_app
from labboard.config import Settings


@pytest.mark.asyncio
async def test_publish_list_download_delete(tmp_path):
    settings = Settings(
        jwt_secret="c" * 32,
        admin_password="correct-horse-battery",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}",
        upload_dir=tmp_path / "uploads",
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
            await client.post("/api/auth/login", json={"password": settings.admin_password})
            csrf = client.cookies.get("labboard_csrf")
            response = await client.post(
                "/api/announcements",
                data={"body": "Welcome to LabBoard"},
                files={"files": ("notes.txt", b"hello", "text/plain")},
                headers={"X-CSRF-Token": csrf},
            )
            assert response.status_code == 201
            announcement = response.json()
            assert announcement["attachments"][0]["original_name"] == "notes.txt"
            listing = await client.get("/api/announcements")
            assert listing.status_code == 200
            download = await client.get(announcement["attachments"][0]["url"])
            assert download.status_code == 200
            assert download.content == b"hello"
            deleted = await client.delete(
                f"/api/announcements/{announcement['id']}", headers={"X-CSRF-Token": csrf}
            )
            assert deleted.status_code == 200
            assert (await client.get("/api/announcements")).json() == []
