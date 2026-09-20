"""Order lifecycle + generation orchestration.

Flow:
    create_order()  -> validates params, resolves template list, computes price,
                       persists a draft order (idempotency-guarded).
    checkout()      -> returns pricing + payment options; for Stars creates an
                       invoice link via the Bot API.
    pay_with_credit / pay_free -> consume credit (or skip for free users) and
                       generate immediately.
    fulfill_stars() -> called after a validated successful_payment with a
                       re-checked (non-stale) price; then generate.

Generation renders each selected template to .tgs (in a bounded thread pool)
and creates/append s a Telegram pack.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import EmojiPack, Order, User
from app.services import (
    catalog_service,
    credit_service,
    pack_service,
    pricing_service,
    referral_service,
    render_service,
    user_service,
)
from app.telegram.bot_client import BotClient, TelegramAPIError

log = logging.getLogger("orders")

# Bounded concurrency so expensive renders don't exhaust the process.
_render_semaphore = asyncio.Semaphore(settings.render_max_concurrency)


class OrderError(Exception):
    """Domain error with an Uzbek-safe message."""


def _price_kind(kind: str) -> str:
    return kind  # name/logo/logo2/logo3/pf all map 1:1 to price kinds


async def create_order(
    session: AsyncSession,
    user: User,
    *,
    kind: str,
    pack_kind: str,
    text: str,
    templates: str,
    outer_hex: Optional[str],
    inner_hex: Optional[str],
    color_hex: Optional[str],
    font_key: Optional[str],
    pack_title: str,
    existing_pack_nick: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Order:
    # Idempotency: return the existing order for a repeated key.
    if idempotency_key:
        existing = (
            await session.execute(
                select(Order).where(Order.idempotency_key == idempotency_key)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

    # Text length limits mirror the original engine.
    text = (text or "").strip()
    if not text:
        raise OrderError("Matn bo'sh bo'lmasligi kerak")
    if kind == "name" and len(text) > settings.name_max_len:
        raise OrderError(f"So'z {settings.name_max_len} ta belgidan oshmasligi kerak")
    if kind == "pf" and len(text) > settings.pf_max_len:
        raise OrderError(f"Matn {settings.pf_max_len} ta belgidan oshmasligi kerak")

    # Resolve template selection.
    try:
        resolved = catalog_service.validate_template_selection(kind, templates)
    except ValueError as e:
        raise OrderError(str(e)) from e

    item_count = len(resolved)
    unit_price = await pricing_service.get_price(session, _price_kind(kind))
    total_price = unit_price * item_count

    params = {
        "text": text,
        "outer_hex": outer_hex,
        "inner_hex": inner_hex,
        "color_hex": color_hex,
        "font_key": font_key,
        "resolved_templates": resolved,
        "existing_pack_nick": existing_pack_nick,
    }

    order = Order(
        user_id=user.id,
        kind=kind,
        pack_kind=pack_kind,
        params_json=json.dumps(params, ensure_ascii=False),
        template_selection=",".join(resolved),
        item_count=item_count,
        unit_price=unit_price,
        total_price=total_price,
        status="draft",
        idempotency_key=idempotency_key,
    )
    order.pack_title = pack_title or f"{catalog_service.section_title(kind)} — {text}"
    session.add(order)
    await session.flush()
    return order


def _order_params(order: Order) -> dict:
    try:
        return json.loads(order.params_json or "{}")
    except json.JSONDecodeError:
        return {}


async def checkout(session: AsyncSession, user: User, order: Order, bot: BotClient) -> dict:
    """Prepare payment options. Re-reads the current price to avoid staleness."""
    if order.user_id != user.id:
        raise OrderError("Buyurtma sizga tegishli emas")
    if order.status not in ("draft", "awaiting_payment"):
        raise OrderError("Bu buyurtma allaqachon yakunlangan")

    # Always re-price at checkout.
    unit_price = await pricing_service.get_price(session, _price_kind(order.kind))
    order.unit_price = unit_price
    order.total_price = unit_price * order.item_count
    order.status = "awaiting_payment"
    await session.flush()

    free = user_service.is_free_user(user)
    credits = await credit_service.get_balance(session, user.id)

    invoice_link = None
    if not free:
        try:
            invoice_link = await bot.create_invoice_link(
                title=f"{catalog_service.section_title(order.kind)}",
                description=f"{order.item_count} ta emoji",
                payload=f"pack:{order.id}",
                prices=[{"label": "Emoji Pack", "amount": order.total_price}],
            )
        except TelegramAPIError as e:
            log.warning("invoice link failed: %s", e)
            invoice_link = None

    return {
        "order_id": order.id,
        "unit_price": order.unit_price,
        "total_price": order.total_price,
        "item_count": order.item_count,
        "currency": "XTR",
        "can_use_credit": (not free) and credits > 0,
        "credits_available": credits,
        "is_free_user": free,
        "invoice_link": invoice_link,
    }


async def _generate(session: AsyncSession, user: User, order: Order, bot: BotClient) -> Order:
    """Render every selected template and create/append the Telegram pack."""
    order.status = "generating"
    await session.flush()

    params = _order_params(order)
    resolved = params.get("resolved_templates") or order.template_selection.split(",")
    text = params.get("text", "")

    # Render each template to .tgs off the event loop (bounded concurrency).
    async def render_one(tpl: str) -> bytes:
        async with _render_semaphore:
            return await asyncio.to_thread(
                render_service.render_tgs,
                order.kind, tpl, text,
                params.get("outer_hex"), params.get("inner_hex"),
                params.get("color_hex"), params.get("font_key"),
            )

    try:
        blobs = await asyncio.gather(*[render_one(t) for t in resolved])
    except Exception as e:  # noqa: BLE001
        order.status = "failed"
        order.error_message = f"Render xatosi: {e}"
        await session.flush()
        raise OrderError(order.error_message) from e

    # Determine nick + title.
    existing_nick = params.get("existing_pack_nick")
    nick = existing_nick or pack_service.random_nick()
    bot_username = settings.bot_username or "bot"

    try:
        pack = await pack_service.create_or_append_pack(
            session, bot,
            owner_id=user.id,
            bot_username=bot_username,
            pack_kind=order.pack_kind,
            nick=nick,
            title=order.pack_title or text,
            sticker_blobs=list(blobs),
            template_refs=resolved,
        )
    except TelegramAPIError as e:
        order.status = "failed"
        order.error_message = f"To'plamga qo'shib bo'lmadi: {e.description}"
        await session.flush()
        raise OrderError(order.error_message) from e

    order.pack_id = pack.id
    order.status = "completed"
    await session.flush()

    # Update aggregates + reward pending referral (first pack).
    user.packs_created = int(user.packs_created) + 1
    await session.flush()
    await referral_service.reward_if_pending(session, user.id)
    return order


async def pay_with_credit(session: AsyncSession, user: User, order: Order, bot: BotClient) -> Order:
    if order.user_id != user.id:
        raise OrderError("Buyurtma sizga tegishli emas")
    if order.status not in ("draft", "awaiting_payment"):
        raise OrderError("Bu buyurtma allaqachon yakunlangan")
    if user_service.is_free_user(user):
        order.payment_method = "free"
        await session.flush()
        return await _generate(session, user, order, bot)

    ok = await credit_service.consume_credit(session, user.id, order_id=order.id)
    if not ok:
        raise OrderError("Bepul kredit yetarli emas")
    order.payment_method = "credit"
    await session.flush()
    try:
        return await _generate(session, user, order, bot)
    except OrderError:
        # Refund the credit if generation failed.
        await credit_service.grant_credit(session, user.id, 1, reason="order_failed_refund", order_id=order.id)
        raise


async def fulfill_after_payment(
    session: AsyncSession, order: Order, paid_amount: int, bot: BotClient
) -> Order:
    """Called from the payment webhook after signature-valid successful_payment.

    Re-checks the price to prevent stale-price delivery. If the paid amount no
    longer matches the current price, the order is flagged and NOT delivered.
    """
    user = await session.get(User, order.user_id)
    current_unit = await pricing_service.get_price(session, _price_kind(order.kind))
    expected = current_unit * order.item_count
    if paid_amount != expected:
        order.status = "cancelled"
        order.error_message = "stale_price"
        await session.flush()
        raise OrderError("Narx o'zgargan — buyurtma yetkazilmadi (refund kerak)")

    order.payment_method = "stars"
    order.status = "paid"
    await session.flush()
    return await _generate(session, user, order, bot)


def order_to_public(order: Order, pack: Optional[EmojiPack] = None) -> dict:
    return {
        "id": order.id,
        "kind": order.kind,
        "pack_kind": order.pack_kind,
        "template_selection": order.template_selection,
        "item_count": order.item_count,
        "unit_price": order.unit_price,
        "total_price": order.total_price,
        "payment_method": order.payment_method,
        "status": order.status,
        "pack_url": pack.telegram_url if pack else None,
        "pack_title": getattr(order, "pack_title", None),
        "error_message": order.error_message,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }
