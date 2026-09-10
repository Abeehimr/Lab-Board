from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "LabBoard"
    environment: str = "development"
    jwt_secret: str = Field(default="", validation_alias="JWT_SECRET")
    admin_password: str = Field(default="", validation_alias="ADMIN_PASSWORD")
    cookie_secure: bool = Field(default=False, validation_alias="COOKIE_SECURE")
    cookie_name: str = "labboard_session"
    database_url: str = Field(default="sqlite+aiosqlite:///./data/labboard.db", validation_alias="DATABASE_URL")
    upload_dir: Path = Field(default=Path("./uploads"), validation_alias="UPLOAD_DIR")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES")
    max_attachments: int = Field(default=5, validation_alias="MAX_ATTACHMENTS")
    rate_limit_per_minute: int = Field(default=10, validation_alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_window_seconds: int = Field(default=60, validation_alias="RATE_LIMIT_WINDOW_SECONDS")
    jwt_expiry_minutes: int = Field(default=8 * 60, validation_alias="JWT_EXPIRY_MINUTES")
    max_announcement_chars: int = Field(default=20_000, validation_alias="MAX_ANNOUNCEMENT_CHARS")
    allowed_upload_extensions: str = Field(
        default=".pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.doc,.docx,.xls,.xlsx,.ppt,.pptx",
        validation_alias="ALLOWED_UPLOAD_EXTENSIONS",
    )

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return value

    @field_validator("admin_password")
    @classmethod
    def validate_admin_password(cls, value: str) -> str:
        if len(value) < 12:
            raise ValueError("ADMIN_PASSWORD must be at least 12 characters")
        return value

    @property
    def allowed_extensions(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_upload_extensions.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
