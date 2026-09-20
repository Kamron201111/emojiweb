"""Auth endpoints — validate Telegram initData and issue a session token."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import issue_token
from app.core.config import settings
from app.core.database import get_session
from app.core.telegram_auth import InitDataError, validate_init_data
from app.schemas import AuthRequest, AuthResponse, UserPublic
from app.services import referral_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_public(user, is_admin: bool) -> UserPublic:
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
        is_admin=is_admin,
        packs_created=user.packs_created,
        stars_spent=user.stars_spent,
    )


@router.post("", response_model=AuthResponse)
@router.post("/", response_model=AuthResponse)
async def authenticate(body: AuthRequest, session: AsyncSession = Depends(get_session)):
    """Validate initData, provision the user, handle referral start_param, and
    return a signed session token + public profile."""
    try:
        data = validate_init_data(
            body.init_data, settings.bot_token,
            max_age_seconds=settings.initdata_max_age_seconds,
        )
    except InitDataError as e:
        raise HTTPException(status_code=401, detail=f"initData xatosi: {e}") from e

    user = await user_service.get_or_create_user(session, data.user)

    # Deep-link referral: start_param = "ref_<id>".
    sp = (data.start_param or "").strip()
    if sp.startswith("ref_"):
        try:
            referrer_id = int(sp[4:])
            await referral_service.record_referral(session, user.id, referrer_id)
        except ValueError:
            pass

    await session.commit()
    token = issue_token(user.id)
    return AuthResponse(token=token, user=_user_public(user, settings.is_admin(user.id)))
