"""App settings (support contact) and required-channel subscription logic."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as cfg
from app.models import RequiredChannel, Setting
from app.telegram.bot_client import BotClient, TelegramAPIError

log = logging.getLogger("settings")

SUPPORT_KEY = "support_contact"


async def get_setting(session: AsyncSession, key: str, default: str = "") -> str:
    row = await session.get(Setting, key)
    return row.value if row else default


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    row = await session.get(Setting, key)
    if row is None:
        session.add(Setting(key=key, value=value))
    else:
        row.value = value
    await session.flush()


async def get_support_contact(session: AsyncSession) -> str:
    return await get_setting(session, SUPPORT_KEY, cfg.default_support_contact)


async def set_support_contact(session: AsyncSession, contact: str) -> None:
    await set_setting(session, SUPPORT_KEY, contact)


async def list_channels(session: AsyncSession, only_enabled: bool = False):
    stmt = select(RequiredChannel).order_by(RequiredChannel.id)
    if only_enabled:
        stmt = stmt.where(RequiredChannel.enabled.is_(True))
    return (await session.execute(stmt)).scalars().all()


async def add_channel(session: AsyncSession, username: str, title: str | None) -> RequiredChannel:
    ch = RequiredChannel(username=username, title=title, enabled=True)
    session.add(ch)
    await session.flush()
    return ch


async def remove_channel(session: AsyncSession, channel_id: int) -> bool:
    ch = await session.get(RequiredChannel, channel_id)
    if ch is None:
        return False
    await session.delete(ch)
    await session.flush()
    return True


async def toggle_channel(session: AsyncSession, channel_id: int, enabled: bool) -> bool:
    ch = await session.get(RequiredChannel, channel_id)
    if ch is None:
        return False
    ch.enabled = enabled
    await session.flush()
    return True


async def is_subscribed(session: AsyncSession, user_id: int, bot: BotClient) -> bool:
    """Verify membership in ALL enabled required channels via the Bot API.

    Never trust a frontend flag — always check server-side. If there are no
    channels, everyone passes.
    """
    channels = await list_channels(session, only_enabled=True)
    if not channels:
        return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch.username, user_id)
            status = (member or {}).get("status")
            if status in ("left", "kicked"):
                return False
        except TelegramAPIError as e:  # noqa: PERF203
            # If the bot can't check (e.g. not admin in channel), skip that one
            # rather than locking everyone out — mirrors original behavior.
            log.warning("channel check failed for %s: %s", ch.username, e)
            continue
    return True
