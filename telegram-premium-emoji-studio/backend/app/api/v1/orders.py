"""Order endpoints: create draft, checkout, pay-with-credit (or free), history."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import default_rate_limit, get_current_user
from app.core.database import get_session
from app.models import EmojiPack, Order, User
from app.schemas import (
    OrderCheckoutResponse,
    OrderCreateRequest,
    OrderPublic,
    PayWithCreditRequest,
)
from app.services import order_service
from app.telegram.bot_client import get_bot

router = APIRouter(prefix="/orders", tags=["orders"])


async def _public(session: AsyncSession, order: Order) -> OrderPublic:
    pack = await session.get(EmojiPack, order.pack_id) if order.pack_id else None
    return OrderPublic(**order_service.order_to_public(order, pack))


@router.post("", response_model=OrderPublic)
async def create_order(
    body: OrderCreateRequest,
    user: User = Depends(default_rate_limit),
    session: AsyncSession = Depends(get_session),
):
    try:
        order = await order_service.create_order(
            session, user,
            kind=body.kind, pack_kind=body.pack_kind, text=body.text,
            templates=body.templates, outer_hex=body.outer_hex, inner_hex=body.inner_hex,
            color_hex=body.color_hex, font_key=body.font_key, pack_title=body.pack_title,
            existing_pack_nick=body.existing_pack_nick, idempotency_key=body.idempotency_key,
        )
    except order_service.OrderError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await session.commit()
    return await _public(session, order)


@router.post("/{order_id}/checkout", response_model=OrderCheckoutResponse)
async def checkout(
    order_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    try:
        result = await order_service.checkout(session, user, order, get_bot())
    except order_service.OrderError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await session.commit()
    return OrderCheckoutResponse(**result)


@router.post("/pay-credit", response_model=OrderPublic)
async def pay_with_credit(
    body: PayWithCreditRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    order = await session.get(Order, body.order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    try:
        order = await order_service.pay_with_credit(session, user, order, get_bot())
    except order_service.OrderError as e:
        await session.commit()
        raise HTTPException(status_code=400, detail=str(e)) from e
    await session.commit()
    return await _public(session, order)


@router.get("", response_model=list[OrderPublic])
async def my_orders(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Order).where(Order.user_id == user.id).order_by(Order.id.desc()).limit(100)
    orders = (await session.execute(stmt)).scalars().all()
    return [await _public(session, o) for o in orders]


@router.get("/{order_id}", response_model=OrderPublic)
async def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    order = await session.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    return await _public(session, order)
