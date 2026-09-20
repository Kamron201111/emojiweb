"""Referral endpoint — link + stats for the current user."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models import User
from app.schemas import ReferralInfo
from app.services import referral_service

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.get("", response_model=ReferralInfo)
async def my_referrals(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    info = await referral_service.referral_info(session, user.id)
    return ReferralInfo(**info)
