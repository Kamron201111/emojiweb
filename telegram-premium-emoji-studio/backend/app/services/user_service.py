"""User provisioning and profile helpers."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.telegram_auth import TelegramUser
from app.models import User


async def get_or_create_user(session: AsyncSession, tg: TelegramUser) -> User:
    """Fetch the user by Telegram id or create it, refreshing profile fields."""
    user = await session.get(User, tg.id)
    if user is None:
        user = User(
            id=tg.id,
            username=tg.username or None,
            first_name=tg.first_name or None,
            last_name=tg.last_name or None,
            language=(tg.language_code or "uz")[:2] if tg.language_code in ("uz", "ru", "en") else "uz",
            is_premium=tg.is_premium,
            photo_url=tg.photo_url or None,
        )
        session.add(user)
    else:
        # Keep profile fresh but don't overwrite an explicit language choice.
        user.username = tg.username or user.username
        user.first_name = tg.first_name or user.first_name
        user.last_name = tg.last_name or user.last_name
        user.is_premium = tg.is_premium
        if tg.photo_url:
            user.photo_url = tg.photo_url
    user.last_seen_at = dt.datetime.now(dt.timezone.utc)
    await session.flush()
    return user


async def set_language(session: AsyncSession, user: User, lang: str) -> None:
    if lang in ("uz", "ru", "en"):
        user.language = lang
        await session.flush()


async def total_users(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count(User.id)))).scalar_one())


async def active_users_since(session: AsyncSession, days: int = 7) -> int:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    stmt = select(func.count(User.id)).where(User.last_seen_at >= cutoff)
    return int((await session.execute(stmt)).scalar_one())


def is_free_user(user: User) -> bool:
    return settings.is_admin(user.id) or bool(user.free_access)
