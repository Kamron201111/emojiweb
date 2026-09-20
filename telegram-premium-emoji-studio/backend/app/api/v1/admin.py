"""Admin dashboard API. Every route requires an admin-verified Telegram
identity (get_admin_user) and writes an AdminAuditLog entry for mutations.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.core.database import get_session
from app.models import (
    AdminAuditLog,
    EmojiPack,
    Order,
    Payment,
    Refund,
    User,
)
from app.schemas import (
    AdminOverview,
    AdminUserRow,
    ChannelCreate,
    ChannelPublic,
    FreeAccessUpdate,
    OrderPublic,
    PriceUpdate,
    RefundAction,
    SupportUpdate,
)
from app.services import (
    credit_service,
    order_service,
    pricing_service,
    settings_service,
    user_service,
)
from app.telegram.bot_client import TelegramAPIError, get_bot

router = APIRouter(prefix="/admin", tags=["admin"])


async def _audit(session: AsyncSession, admin_id: int, action: str, detail: str = ""):
    session.add(AdminAuditLog(admin_id=admin_id, action=action, detail=detail))
    await session.flush()


# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------
@router.get("/overview", response_model=AdminOverview)
async def overview(
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    total_users = await user_service.total_users(session)
    active = await user_service.active_users_since(session, 7)
    total_generations = int((await session.execute(
        select(func.count(Order.id)).where(Order.status == "completed")
    )).scalar_one())
    total_packs = int((await session.execute(select(func.count(EmojiPack.id)))).scalar_one())
    stars_revenue = int((await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == "paid")
    )).scalar_one())
    credits_consumed = int((await session.execute(
        select(func.coalesce(func.sum(func.abs(Order.item_count)), 0)).where(Order.payment_method == "credit")
    )).scalar_one())

    recent = (await session.execute(
        select(Order).order_by(desc(Order.id)).limit(10)
    )).scalars().all()
    recent_public = []
    for o in recent:
        pack = await session.get(EmojiPack, o.pack_id) if o.pack_id else None
        recent_public.append(OrderPublic(**order_service.order_to_public(o, pack)))

    return AdminOverview(
        total_users=total_users,
        active_users_7d=active,
        total_generations=total_generations,
        total_packs=total_packs,
        stars_revenue=stars_revenue,
        credits_consumed=credits_consumed,
        recent_orders=recent_public,
    )


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------
@router.get("/users", response_model=list[AdminUserRow])
async def list_users(
    q: str | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(User).order_by(desc(User.stars_spent)).limit(limit)
    if q:
        like = f"%{q.strip().lstrip('@')}%"
        if q.strip().lstrip("-").isdigit():
            stmt = select(User).where(User.id == int(q.strip())).limit(limit)
        else:
            stmt = select(User).where(User.username.ilike(like)).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        AdminUserRow(
            id=u.id, username=u.username,
            created_at=u.created_at.isoformat() if u.created_at else None,
            packs_created=u.packs_created, stars_spent=u.stars_spent,
            credits=u.credits, free_access=u.free_access,
        )
        for u in rows
    ]


@router.post("/users/free-access")
async def set_free_access(
    body: FreeAccessUpdate,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    u = await session.get(User, body.user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    u.free_access = bool(body.grant)
    await _audit(session, admin.id, "free_access", f"user={body.user_id} grant={body.grant}")
    await session.commit()
    return {"ok": True, "user_id": u.id, "free_access": u.free_access}


@router.post("/users/{user_id}/grant-credit")
async def grant_credit(
    user_id: int,
    amount: int = Query(1, ge=1, le=1000),
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    balance = await credit_service.grant_credit(session, user_id, amount, reason="admin_grant")
    await _audit(session, admin.id, "grant_credit", f"user={user_id} amount={amount}")
    await session.commit()
    return {"ok": True, "user_id": user_id, "credits": balance}


# --------------------------------------------------------------------------
# Pricing
# --------------------------------------------------------------------------
@router.get("/prices")
async def get_prices(
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    prices = await pricing_service.all_prices(session)
    await session.commit()
    return prices


@router.put("/prices")
async def update_price(
    body: PriceUpdate,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    await pricing_service.set_price(session, body.kind, body.stars)
    await _audit(session, admin.id, "set_price", f"{body.kind}={body.stars}")
    await session.commit()
    return {"ok": True, "kind": body.kind, "stars": body.stars}


# --------------------------------------------------------------------------
# Required channels
# --------------------------------------------------------------------------
@router.get("/channels", response_model=list[ChannelPublic])
async def list_channels(
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    chans = await settings_service.list_channels(session)
    return [
        ChannelPublic(id=c.id, username=c.username, title=c.title, enabled=c.enabled,
                      url=f"https://t.me/{c.username.lstrip('@')}")
        for c in chans
    ]


@router.post("/channels", response_model=ChannelPublic)
async def add_channel(
    body: ChannelCreate,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    ch = await settings_service.add_channel(session, body.username, body.title)
    await _audit(session, admin.id, "add_channel", body.username)
    await session.commit()
    return ChannelPublic(id=ch.id, username=ch.username, title=ch.title, enabled=ch.enabled,
                         url=f"https://t.me/{ch.username.lstrip('@')}")


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    ok = await settings_service.remove_channel(session, channel_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Kanal topilmadi")
    await _audit(session, admin.id, "remove_channel", str(channel_id))
    await session.commit()
    return {"ok": True}


@router.put("/channels/{channel_id}/toggle")
async def toggle_channel(
    channel_id: int,
    enabled: bool = Query(...),
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    ok = await settings_service.toggle_channel(session, channel_id, enabled)
    if not ok:
        raise HTTPException(status_code=404, detail="Kanal topilmadi")
    await _audit(session, admin.id, "toggle_channel", f"{channel_id}={enabled}")
    await session.commit()
    return {"ok": True, "enabled": enabled}


# --------------------------------------------------------------------------
# Support contact
# --------------------------------------------------------------------------
@router.put("/support")
async def update_support(
    body: SupportUpdate,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    await settings_service.set_support_contact(session, body.contact)
    await _audit(session, admin.id, "set_support", body.contact)
    await session.commit()
    return {"ok": True, "support_contact": body.contact}


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------
@router.get("/statistics")
async def statistics(
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    # Top users by packs and stars.
    top_packs = (await session.execute(
        select(User.id, User.username, User.packs_created)
        .order_by(desc(User.packs_created)).limit(10)
    )).all()
    top_stars = (await session.execute(
        select(User.id, User.username, User.stars_spent)
        .order_by(desc(User.stars_spent)).limit(10)
    )).all()
    # Popular templates.
    popular = (await session.execute(
        select(Order.template_selection, func.count(Order.id).label("c"))
        .where(Order.status == "completed")
        .group_by(Order.template_selection)
        .order_by(desc("c")).limit(10)
    )).all()
    # Daily activity (last 14 days).
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=14)
    daily = (await session.execute(
        select(func.date(Order.created_at).label("d"), func.count(Order.id))
        .where(Order.created_at >= since)
        .group_by("d").order_by("d")
    )).all()

    return {
        "top_by_packs": [{"id": r[0], "username": r[1], "packs": r[2]} for r in top_packs],
        "top_by_stars": [{"id": r[0], "username": r[1], "stars": r[2]} for r in top_stars],
        "popular_templates": [{"selection": r[0], "count": r[1]} for r in popular],
        "daily_activity": [{"date": str(r[0]), "count": r[1]} for r in daily],
    }


# --------------------------------------------------------------------------
# Payments & refunds
# --------------------------------------------------------------------------
@router.get("/payments")
async def list_payments(
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(
        select(Payment).order_by(desc(Payment.id)).limit(limit)
    )).scalars().all()
    return [
        {
            "id": p.id, "user_id": p.user_id, "purpose": p.purpose, "amount": p.amount,
            "status": p.status, "refunded": p.refunded,
            "charge_id": p.telegram_payment_charge_id,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in rows
    ]


@router.get("/refunds")
async def list_refunds(
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(
        select(Refund).order_by(desc(Refund.id)).limit(100)
    )).scalars().all()
    return [
        {
            "id": r.id, "user_id": r.user_id, "amount": r.amount, "status": r.status,
            "charge_id": r.charge_id, "reason": r.reason,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/refunds/perform")
async def perform_refund(
    body: RefundAction,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    r = await session.get(Refund, body.refund_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Refund topilmadi")
    if r.status == "done":
        return {"ok": True, "already": True}
    bot = get_bot()
    try:
        await bot.refund_star_payment(r.user_id, r.charge_id)
    except TelegramAPIError as e:
        r.status = "failed"
        await session.commit()
        raise HTTPException(status_code=502, detail=f"Refund amalga oshmadi: {e.description}") from e
    r.status = "done"
    r.admin_id = admin.id
    r.done_at = dt.datetime.now(dt.timezone.utc)
    await _audit(session, admin.id, "refund", f"refund_id={r.id} user={r.user_id} amount={r.amount}")
    await session.commit()
    return {"ok": True}
