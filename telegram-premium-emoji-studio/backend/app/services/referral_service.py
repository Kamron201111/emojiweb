"""Referral system — records who invited whom and rewards the referrer with a
free credit after the referred user's FIRST successful pack.

Anti-abuse:
    * self-referral rejected
    * only the first referrer for a user counts (duplicate ignored)
    * reward granted exactly once (``rewarded`` flag, idempotent)
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Referral
from app.services import credit_service


async def record_referral(session: AsyncSession, referred_id: int, referrer_id: int) -> bool:
    if referred_id == referrer_id:
        return False
    existing = await session.get(Referral, referred_id)
    if existing is not None:
        return False
    session.add(Referral(referred_id=referred_id, referrer_id=referrer_id, rewarded=False))
    await session.flush()
    return True


async def reward_if_pending(session: AsyncSession, referred_id: int) -> int | None:
    """Grant the referrer a credit for this referred user's first pack.

    Returns the referrer id if a reward was granted, else None.
    """
    entry = await session.get(Referral, referred_id)
    if entry is None or entry.rewarded:
        return None
    entry.rewarded = True
    entry.rewarded_at = dt.datetime.now(dt.timezone.utc)
    await session.flush()
    await credit_service.grant_credit(
        session, entry.referrer_id, amount=1, reason="referral_reward"
    )
    return entry.referrer_id


async def referral_info(session: AsyncSession, user_id: int) -> dict:
    invited = (
        await session.execute(
            select(func.count(Referral.referred_id)).where(Referral.referrer_id == user_id)
        )
    ).scalar_one()
    successful = (
        await session.execute(
            select(func.count(Referral.referred_id)).where(
                Referral.referrer_id == user_id, Referral.rewarded.is_(True)
            )
        )
    ).scalar_one()
    bot_username = settings.bot_username or "your_bot"
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    return {
        "link": link,
        "invited_count": int(invited),
        "successful_count": int(successful),
        "earned_credits": int(successful),  # 1 credit per successful referral
    }
