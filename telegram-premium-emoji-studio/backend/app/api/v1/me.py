"""Current-user endpoints: profile, language, credits."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_session
from app.models import User
from app.schemas import CreditBalance, CreditTxnPublic, UserPublic
from app.services import credit_service, user_service

router = APIRouter(tags=["me"])


def _user_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=" ".join(p for p in (user.first_name or "", user.last_name or "") if p).strip(),
        language=user.language,
        is_premium=user.is_premium,
        photo_url=user.photo_url,
        credits=user.credits,
        free_access=user.free_access,
        is_admin=settings.is_admin(user.id),
        packs_created=user.packs_created,
        stars_spent=user.stars_spent,
    )


@router.get("/me", response_model=UserPublic)
async def get_me(user: User = Depends(get_current_user)):
    return _user_public(user)


class LanguageUpdate(BaseModel):
    language: str


@router.put("/me/language", response_model=UserPublic)
async def set_language(
    body: LanguageUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await user_service.set_language(session, user, body.language)
    await session.commit()
    return _user_public(user)


@router.get("/credits", response_model=CreditBalance)
async def get_credits(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    txns = await credit_service.list_transactions(session, user.id)
    return CreditBalance(
        credits=user.credits,
        transactions=[
            CreditTxnPublic(
                amount=t.amount, reason=t.reason, balance_after=t.balance_after,
                created_at=t.created_at.isoformat() if t.created_at else None,
            )
            for t in txns
        ],
    )
