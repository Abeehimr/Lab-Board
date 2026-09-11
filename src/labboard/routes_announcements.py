from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import get_session
from .models import Announcement, Attachment
from .schemas import AnnouncementRead, AttachmentRead, MessageResponse
from .security import require_csrf
from .storage import save_upload, stored_path

router = APIRouter(prefix="/api", tags=["announcements"])


def serialize_announcement(item: Announcement, request: Request) -> AnnouncementRead:
    base_url = request.app.state.settings.public_base_url.rstrip("/")
    return AnnouncementRead(
        id=item.id,
        body=item.body,
        created_at=item.created_at,
        attachments=[
            AttachmentRead(
                id=attachment.id,
                original_name=attachment.original_name,
                content_type=attachment.content_type,
                size=attachment.size,
                url=f"{base_url}{request.url_for('download_attachment', attachment_id=attachment.id).path}",
            )
            for attachment in item.attachments
        ],
    )


@router.get("/announcements", response_model=list[AnnouncementRead])
async def list_announcements(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.scalars(
        select(Announcement)
        .options(selectinload(Announcement.attachments))
        .order_by(Announcement.created_at.desc(), Announcement.id.desc())
    )
    return [serialize_announcement(item, request) for item in result.all()]


@router.post("/announcements", response_model=AnnouncementRead, status_code=status.HTTP_201_CREATED)
async def publish_announcement(
    request: Request,
    body: str = Form(...),
    files: list[UploadFile] | None = File(default=None),
    _: dict[str, object] = Depends(require_csrf),
    session: AsyncSession = Depends(get_session),
):
    settings = request.app.state.settings
    body = body.strip()
    if not body or len(body) > settings.max_announcement_chars:
        raise HTTPException(status_code=400, detail="Invalid announcement")
    uploads = [upload for upload in (files or []) if upload.filename]
    if len(uploads) > settings.max_attachments:
        raise HTTPException(status_code=400, detail="Too many attachments")
    announcement = Announcement(body=body)
    session.add(announcement)
    saved_paths: list[Path] = []
    try:
        for upload in uploads:
            original_name, stored_name, size = await save_upload(upload, settings)
            saved_paths.append(stored_path(settings, stored_name))
            announcement.attachments.append(
                Attachment(
                    original_name=original_name,
                    stored_name=stored_name,
                    content_type=upload.content_type or "application/octet-stream",
                    size=size,
                )
            )
        await session.commit()
        await session.refresh(announcement)
        await session.refresh(announcement, attribute_names=["attachments"])
        await request.app.state.event_broker.publish("announcement", {"action": "published", "id": announcement.id})
    except Exception:
        await session.rollback()
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise
    return serialize_announcement(announcement, request)


@router.delete("/announcements/{announcement_id}", response_model=MessageResponse)
async def delete_announcement(
    announcement_id: int,
    request: Request,
    _: dict[str, object] = Depends(require_csrf),
    session: AsyncSession = Depends(get_session),
):
    item = await session.scalar(
        select(Announcement).options(selectinload(Announcement.attachments)).where(Announcement.id == announcement_id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    paths = [stored_path(request.app.state.settings, attachment.stored_name) for attachment in item.attachments]
    await session.delete(item)
    await session.commit()
    await request.app.state.event_broker.publish("announcement", {"action": "deleted", "id": announcement_id})
    for path in paths:
        path.unlink(missing_ok=True)
    return MessageResponse(message="Announcement deleted")


@router.get("/attachments/{attachment_id}", name="download_attachment")
async def download_attachment(attachment_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    attachment = await session.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    path = stored_path(request.app.state.settings, attachment.stored_name)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=attachment.original_name,
        content_disposition_type="attachment",
    )
