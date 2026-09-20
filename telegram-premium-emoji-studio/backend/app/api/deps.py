"""FastAPI dependencies: authentication, current user, admin guard, rate limit.

Authentication accepts the Telegram initData either as a signed session token
(issued by /auth) or as the raw initData in the ``Authorization`` header. Either
way the user id is derived ONLY from cryptographically validated data.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Optional

import itsdangerous
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.telegram_auth import (
    InitDataError,
    TelegramUser,
    validate_init_data,
)
from app.models import User
from app.services import user_service

_signer = itsdangerous.TimestampSigner(settings.secret_key)


def issue_token(user_id: int) -> str:
    return _signer.sign(str(user_id).encode()).decode()


def verify_token(token: str) -> Optional[int]:
    try:
        raw = _signer.unsign(token, max_age=settings.auth_ttl_seconds)
        return int(raw.decode())
    except (itsdangerous.BadSignature, itsdangerous.SignatureExpired, ValueError):
        return None


def _extract_credential(authorization: Optional[str], x_init_data: Optional[str]) -> tuple[str, str]:
    """Return (scheme, value). scheme in {tma, bearer, raw}."""
    if x_init_data:
        return "tma", x_init_data
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2:
            scheme, value = parts[0].lower(), parts[1]
            if scheme == "tma":
                return "tma", value
            if scheme == "bearer":
                return "bearer", value
        return "raw", authorization
    return "", ""


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_init_data: Optional[str] = Header(default=None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
) -> User:
    scheme, value = _extract_credential(authorization, x_init_data)
    if not value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Avtorizatsiya talab qilinadi")

    user_id: Optional[int] = None
    tg_user: Optional[TelegramUser] = None

    if scheme == "bearer":
        user_id = verify_token(value)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token yaroqsiz yoki muddati o'tgan")
    else:
        # tma / raw -> validate initData cryptographically.
        try:
            data = validate_init_data(
                value, settings.bot_token,
                max_age_seconds=settings.initdata_max_age_seconds,
            )
            tg_user = data.user
            user_id = tg_user.id
        except InitDataError as e:
            raise HTTPException(status_code=401, detail=f"initData xatosi: {e}") from e

    if tg_user is not None:
        user = await user_service.get_or_create_user(session, tg_user)
    else:
        user = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="Foydalanuvchi topilmadi")
    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not settings.is_admin(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Faqat administratorlar uchun")
    return user


# --------------------------------------------------------------------------
# Simple in-memory sliding-window rate limiter (per user + route bucket).
# --------------------------------------------------------------------------
_hits: dict[str, deque] = defaultdict(deque)


class RateLimiter:
    def __init__(self, per_minute: int, bucket: str):
        self.per_minute = per_minute
        self.bucket = bucket

    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        key = f"{self.bucket}:{user.id}"
        now = time.time()
        dq = _hits[key]
        while dq and now - dq[0] > 60:
            dq.popleft()
        if len(dq) >= self.per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Juda ko'p so'rov — biroz kuting",
            )
        dq.append(now)
        return user


preview_rate_limit = RateLimiter(settings.rate_limit_preview_per_min, "preview")
default_rate_limit = RateLimiter(settings.rate_limit_default_per_min, "default")
