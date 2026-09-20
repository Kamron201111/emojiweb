"""Public settings + subscription-check endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings as cfg
from app.core.database import get_session
from app.models import User
from app.schemas import ChannelPublic, SettingsPublic, SubscriptionStatus
from app.services import pricing_service, settings_service
from app.telegram.bot_client import get_bot

router = APIRouter(prefix="/settings", tags=["settings"])


def _channel_public(ch) -> ChannelPublic:
    return ChannelPublic(
        id=ch.id, username=ch.username, title=ch.title, enabled=ch.enabled,
        url=f"https://t.me/{ch.username.lstrip('@')}",
    )


@router.get("", response_model=SettingsPublic)
async def public_settings(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    support = await settings_service.get_support_contact(session)
    channels = await settings_service.list_channels(session, only_enabled=True)
    prices = await pricing_service.all_prices(session)
    await session.commit()
    return SettingsPublic(
        support_contact=support,
        required_channels=[_channel_public(c) for c in channels],
        prices=prices,
        gift_min_amount=cfg.gift_min_amount,
        gift_max_amount=cfg.gift_max_amount,
        name_max_len=cfg.name_max_len,
        pf_max_len=cfg.pf_max_len,
    )


@router.get("/subscription", response_model=SubscriptionStatus)
async def subscription_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    channels = await settings_service.list_channels(session, only_enabled=True)
    subscribed = await settings_service.is_subscribed(session, user.id, get_bot())
    return SubscriptionStatus(
        subscribed=subscribed,
        channels=[_channel_public(c) for c in channels],
    )
