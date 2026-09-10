from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=512)


class MessageResponse(BaseModel):
    message: str


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_name: str
    content_type: str
    size: int
    url: str


class AnnouncementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    created_at: datetime
    attachments: list[AttachmentRead] = Field(default_factory=list)
