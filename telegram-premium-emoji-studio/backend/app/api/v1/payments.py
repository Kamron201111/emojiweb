"""Payment endpoints.

Telegram Stars payments are completed via Telegram's own UI (invoice link is
created server-side in orders.checkout / gift). Telegram then delivers a
``pre_checkout_query`` and a ``successful_payment`` update to the bot webhook.

This module exposes:
    * POST /payments/gift          -> create a Stars gift invoice link
    * POST /payments/telegram-webhook -> receive pre_checkout & successful_payment

Duplicate protection: a payment is keyed by ``telegram_payment_charge_id``
(unique). If we've already recorded a charge id, we skip re-fulfilling it.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_session
from app.models import Order, Payment, Refund, User
from app.schemas import GiftRequest, GiftResponse
from app.services import order_service
from app.telegram.bot_client import TelegramAPIError, get_bot

log = logging.getLogger("payments")
router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/gift", response_model=GiftResponse)
async def create_gift(
    body: GiftRequest,
    user: User = Depends(get_current_user),
):
    amount = body.amount
    if not (settings.gift_min_amount <= amount <= settings.gift_max_amount):
        raise HTTPException(
            status_code=422,
            detail=f"Miqdor {settings.gift_min_amount}–{settings.gift_max_amount} orasida bo'lsin",
        )
    bot = get_bot()
    try:
        link = await bot.create_invoice_link(
            title="⭐ Yulduz hadya",
            description=f"{amount} ⭐ Stars hadya qilish",
            payload=f"gift:{user.id}:{amount}",
            prices=[{"label": "Stars hadya", "amount": amount}],
        )
    except TelegramAPIError as e:
        raise HTTPException(status_code=502, detail=f"Invoys yaratib bo'lmadi: {e.description}") from e
    return GiftResponse(invoice_link=link, amount=amount)


async def _already_processed(session: AsyncSession, charge_id: str) -> bool:
    if not charge_id:
        return False
    existing = (
        await session.execute(
            select(Payment).where(Payment.telegram_payment_charge_id == charge_id)
        )
    ).scalar_one_or_none()
    return existing is not None


@router.post("/telegram-webhook")
async def telegram_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    """Receive Telegram updates for payments.

    Set the webhook with a secret_token and configure WEBHOOK_SECRET to match;
    we verify the header before trusting the update.
    """
    expected = settings.secret_key[:32]
    if x_telegram_bot_api_secret_token and x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=403, detail="Webhook secret mos emas")

    update = await request.json()
    bot = get_bot()

    # 1) Pre-checkout — must answer within seconds.
    pcq = update.get("pre_checkout_query")
    if pcq:
        try:
            await bot.answer_pre_checkout_query(pcq["id"], ok=True)
        except TelegramAPIError as e:
            log.warning("pre_checkout answer failed: %s", e)
        return {"ok": True}

    # 2) Successful payment.
    msg = update.get("message") or {}
    sp = msg.get("successful_payment")
    if not sp:
        return {"ok": True}

    payload = sp.get("invoice_payload", "")
    charge_id = sp.get("telegram_payment_charge_id", "")
    total_amount = int(sp.get("total_amount", 0))
    from_user = (msg.get("from") or {}).get("id")

    # Duplicate guard.
    if await _already_processed(session, charge_id):
        return {"ok": True, "duplicate": True}

    parts = payload.split(":")
    purpose = parts[0] if parts else ""

    if purpose == "gift":
        session.add(Payment(
            user_id=from_user, purpose="gift", amount=total_amount, currency="XTR",
            telegram_payment_charge_id=charge_id, invoice_payload=payload, status="paid",
        ))
        # Track stars spent.
        u = await session.get(User, from_user)
        if u:
            u.stars_spent = int(u.stars_spent) + total_amount
        await session.commit()
        try:
            await bot.send_message(from_user, f"✅ Rahmat! {total_amount} ⭐ hadyangiz uchun tashakkur 🙏")
        except TelegramAPIError:
            pass
        return {"ok": True}

    if purpose == "pack" and len(parts) >= 2:
        try:
            order_id = int(parts[1])
        except ValueError:
            return {"ok": True}
        order = await session.get(Order, order_id)
        if order is None:
            return {"ok": True}

        payment = Payment(
            order_id=order.id, user_id=order.user_id, purpose="pack",
            amount=total_amount, currency="XTR",
            telegram_payment_charge_id=charge_id, invoice_payload=payload, status="paid",
        )
        session.add(payment)

        u = await session.get(User, order.user_id)
        if u:
            u.stars_spent = int(u.stars_spent) + total_amount

        try:
            await order_service.fulfill_after_payment(session, order, total_amount, bot)
            await session.commit()
        except order_service.OrderError:
            # Stale price or generation failure -> queue a refund.
            payment.status = "refunded"
            payment.refunded = True
            session.add(Refund(
                payment_id=payment.id, user_id=order.user_id, charge_id=charge_id,
                amount=total_amount, status="pending", reason="stale_price_or_fail",
            ))
            await session.commit()
            # Notify + auto-attempt refund.
            try:
                await bot.refund_star_payment(order.user_id, charge_id)
            except TelegramAPIError as e:
                log.warning("auto-refund failed: %s", e)
        else:
            # Notify success with pack link.
            from app.models import EmojiPack
            pack = await session.get(EmojiPack, order.pack_id) if order.pack_id else None
            if pack:
                try:
                    await bot.send_message(
                        order.user_id,
                        f"✅ Tayyor! Mana emojingiz, to'lov uchun rahmat 🙏\n{pack.telegram_url}",
                    )
                except TelegramAPIError:
                    pass
        return {"ok": True}

    return {"ok": True}
