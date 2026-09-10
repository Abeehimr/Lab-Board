from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .database import create_engine, create_session_factory, init_database
from .schemas import HealthResponse


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
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
    application.dependency_overrides[__import__("labboard.database", fromlist=["get_session"]).get_session] = (
        session_dependency
    )

    @application.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    return application


app = create_app()
