"""Pack creation — creates or appends a Telegram sticker/emoji set from
rendered .tgs bytes, reusing the original bot's storage-key convention so packs
can be reused/appended, and mirroring its rate-limit-safe add loop.
"""
from __future__ import annotations

import random
import re
import string
from typing import Awaitable, Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmojiPack, PackItem
from app.telegram.bot_client import BotClient, TelegramAPIError


def random_nick(length: int = 12) -> str:
    """Telegram-style random lowercase nick, e.g. 'wiwheowuwhsj'."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def safe_nick(nick: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", nick or "")
    return cleaned or "pack"


ProgressCb = Optional[Callable[[int, int], Awaitable[None]]]


async def _find_pack(session: AsyncSession, owner_id: int, pack_kind: str, nick: str) -> Optional[EmojiPack]:
    stmt = select(EmojiPack).where(
        EmojiPack.owner_id == owner_id,
        EmojiPack.pack_kind == pack_kind,
        EmojiPack.nick == nick,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_or_append_pack(
    session: AsyncSession,
    bot: BotClient,
    *,
    owner_id: int,
    bot_username: str,
    pack_kind: str,
    nick: str,
    title: str,
    sticker_blobs: list[bytes],
    template_refs: Optional[list[str]] = None,
    progress: ProgressCb = None,
) -> EmojiPack:
    """Create a new set (or append to an existing one for this nick) and add
    all rendered stickers. Returns the persisted :class:`EmojiPack`.

    Raises TelegramAPIError on unrecoverable failures.
    """
    sticker_type = "custom_emoji" if pack_kind == "emoji" else "regular"
    template_refs = template_refs or [""] * len(sticker_blobs)
    total = len(sticker_blobs)

    pack = await _find_pack(session, owner_id, pack_kind, nick)
    set_name = pack.set_name if pack else f"{safe_nick(nick)}_{owner_id}_by_{bot_username}"

    for i, blob in enumerate(sticker_blobs):
        if i == 0 and pack is None:
            try:
                await bot.create_new_sticker_set(
                    user_id=owner_id, name=set_name, title=title or nick,
                    sticker_bytes=blob, sticker_type=sticker_type,
                )
            except TelegramAPIError as e:
                if "occupied" not in str(e).lower():
                    raise
                # Name already taken by us — just append.
                await bot.add_sticker_to_set(user_id=owner_id, name=set_name, sticker_bytes=blob)
            # Persist the pack row now that the set exists.
            pack = EmojiPack(
                owner_id=owner_id, pack_kind=pack_kind, nick=nick,
                title=title or nick, set_name=set_name, item_count=0,
            )
            session.add(pack)
            await session.flush()
        else:
            await bot.add_sticker_to_set(user_id=owner_id, name=set_name, sticker_bytes=blob)

        pack.item_count += 1
        session.add(PackItem(pack_id=pack.id, template_ref=template_refs[i] if i < len(template_refs) else ""))
        await session.flush()
        if progress:
            await progress(i + 1, total)

    return pack
