from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "LabBoard"
    environment: str = "development"
    jwt_secret: str = Field(default="", validation_alias="JWT_SECRET")
    jwt_secret_file: Path = Field(default=Path("./data/.jwt_secret"), validation_alias="JWT_SECRET_FILE")
    admin_password: str = Field(default="", validation_alias="ADMIN_PASSWORD")
    cookie_secure: bool = Field(default=False, validation_alias="COOKIE_SECURE")
    cookie_name: str = "labboard_session"
    database_url: str = Field(default="sqlite+aiosqlite:///./data/labboard.db", validation_alias="DATABASE_URL")
    upload_dir: Path = Field(default=Path("./uploads"), validation_alias="UPLOAD_DIR")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES")
    max_attachments: int = Field(default=5, validation_alias="MAX_ATTACHMENTS")
    rate_limit_per_minute: int = Field(default=10, validation_alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_window_seconds: int = Field(default=60, validation_alias="RATE_LIMIT_WINDOW_SECONDS")
    jwt_expiry_minutes: int = Field(default=5 * 60, validation_alias="JWT_EXPIRY_MINUTES")
    max_announcement_chars: int = Field(default=20_000, validation_alias="MAX_ANNOUNCEMENT_CHARS")
    allowed_upload_extensions: str = Field(
        default=".pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.doc,.docx,.xls,.xlsx,.ppt,.pptx",
        validation_alias="ALLOWED_UPLOAD_EXTENSIONS",
    )

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if value and len(value) < 32:
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

    def resolve_jwt_secret(self) -> str:
        if self.jwt_secret:
            return self.jwt_secret

        self.jwt_secret_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            secret = self.jwt_secret_file.read_text(encoding="ascii").strip()
        except FileNotFoundError:
            secret = secrets.token_urlsafe(48)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            try:
                file_descriptor = os.open(self.jwt_secret_file, flags, 0o600)
            except FileExistsError:
                secret = self.jwt_secret_file.read_text(encoding="ascii").strip()
            else:
                with os.fdopen(file_descriptor, "w", encoding="ascii") as handle:
                    handle.write(secret + "\n")
        if len(secret) < 32:
            raise ValueError("Generated JWT secret file is missing or unsafe")
        self.jwt_secret = secret
        return secret


@lru_cache
def get_settings() -> Settings:
    return Settings()
