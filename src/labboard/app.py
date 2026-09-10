from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .database import create_engine, create_session_factory, init_database
from .events import EventBroker
from .routes_auth import router as auth_router
from .routes_announcements import router as announcements_router
from .routes_events import router as events_router
from .schemas import HealthResponse
from .security import RateLimiter, hash_password


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.resolve_jwt_secret()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await init_database(engine, settings)
        yield
        await engine.dispose()

    application = FastAPI(title=settings.app_name, lifespan=lifespan)

    async def session_dependency() -> AsyncSession:
        async with session_factory() as session:
            yield session

    application.state.settings = settings
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.state.admin_password_hash = hash_password(settings.admin_password)
    application.state.login_limiter = RateLimiter(
        settings.rate_limit_per_minute, settings.rate_limit_window_seconds
    )
    application.state.event_broker = EventBroker()
    application.dependency_overrides[__import__("labboard.database", fromlist=["get_session"]).get_session] = (
        session_dependency
    )
    application.include_router(auth_router)
    application.include_router(announcements_router)
    application.include_router(events_router)

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, __: RequestValidationError):
        return JSONResponse(status_code=400, content={"detail": "Invalid request"})

    @application.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    @application.get("/admin", include_in_schema=False)
    @application.get("/admin/", include_in_schema=False)
    async def admin_page() -> FileResponse:
        return FileResponse(frontend_dir / "index.html", media_type="text/html")

    @application.get("/admin/login", include_in_schema=False)
    @application.get("/admin/login/", include_in_schema=False)
    async def admin_login_page() -> FileResponse:
        return FileResponse(frontend_dir / "login.html", media_type="text/html")

    application.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return application


app = create_app()
