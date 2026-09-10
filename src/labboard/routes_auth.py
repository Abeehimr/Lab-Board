from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from .schemas import LoginRequest, MessageResponse
from .security import (
    RateLimiter,
    create_token,
    hash_password,
    require_admin,
    require_csrf,
    request_ip,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=MessageResponse)
async def login(payload: LoginRequest, request: Request, response: Response) -> MessageResponse:
    settings = request.app.state.settings
    limiter: RateLimiter = request.app.state.login_limiter
    key = request_ip(request)
    if not limiter.allow(key):
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": str(limiter.retry_after(key))},
        )
    if not verify_password(payload.password, request.app.state.admin_password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        settings.cookie_name,
        create_token(settings, csrf_token),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expiry_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "labboard_csrf",
        csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expiry_minutes * 60,
        path="/",
    )
    return MessageResponse(message="Logged in")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    _: dict[str, object] = Depends(require_csrf),
) -> MessageResponse:
    settings = request.app.state.settings
    response.delete_cookie(settings.cookie_name, path="/")
    response.delete_cookie("labboard_csrf", path="/")
    return MessageResponse(message="Logged out")


@router.get("/status", response_model=MessageResponse)
async def auth_status(_: dict[str, object] = Depends(require_admin)) -> MessageResponse:
    return MessageResponse(message="authenticated")
