"""SQLAlchemy ORM models for Telegram Premium Emoji Studio.

Designed after analyzing the original bot's JSON stores (users, credits,
referrals, stats, prices, settings, emoji_pack, refund_requests) and normalizing
them into proper relational tables with transactional guarantees.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = "users"

    # Telegram user id is the primary key (stable, unique).
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    language: Mapped[str] = mapped_column(String(4), default="uz")
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    photo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Free (no-pay) access — mirrors the old allowed_users.json.
    free_access: Mapped[bool] = mapped_column(Boolean, default=False)

    # Free credits balance (mirrors credits.json). Mutated only inside a
    # transaction with row locking to prevent double-spend.
    credits: Mapped[int] = mapped_column(Integer, default=0)

    # Cached aggregates for fast leaderboards (also derivable from orders).
    packs_created: Mapped[int] = mapped_column(Integer, default=0)
    stars_spent: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    credit_transactions: Mapped[list["CreditTransaction"]] = relationship(back_populates="user")


class ProductPrice(Base):
    """Price per product kind in Telegram Stars. Editable from admin panel.

    kinds: name, logo, logo2, logo3, pf, code
    """
    __tablename__ = "product_prices"

    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Order(Base):
    """A generation order. Tracks the full lifecycle from draft to delivered."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)

    kind: Mapped[str] = mapped_column(String(16))  # name|logo|logo2|logo3|pf
    pack_kind: Mapped[str] = mapped_column(String(16), default="emoji")  # emoji|sticker

    # Snapshot of the creation parameters (JSON-encoded text).
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    template_selection: Mapped[str] = mapped_column(String(255), default="")
    item_count: Mapped[int] = mapped_column(Integer, default=1)
    pack_title: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Pricing snapshot captured at checkout to prevent stale-price purchases.
    unit_price: Mapped[int] = mapped_column(Integer, default=0)
    total_price: Mapped[int] = mapped_column(Integer, default=0)

    # Payment method: stars | credit | free
    payment_method: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    # State machine: draft -> awaiting_payment -> paid -> generating ->
    #                completed | failed | cancelled | refunded
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)

    # Idempotency key to protect against duplicate submissions/double-clicks.
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)

    pack_id: Mapped[Optional[int]] = mapped_column(ForeignKey("emoji_packs.id"), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="orders")
    payment: Mapped[Optional["Payment"]] = relationship(back_populates="order", uselist=False)
    pack: Mapped[Optional["EmojiPack"]] = relationship(back_populates="orders")


class Payment(Base):
    """Telegram Stars payment record with idempotency + refund tracking."""
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)

    purpose: Mapped[str] = mapped_column(String(16))  # pack|gift|code
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="XTR")

    # Telegram's unique charge id — the anchor for refunds and duplicate guard.
    telegram_payment_charge_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, unique=True
    )
    invoice_payload: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(24), default="pending")  # pending|paid|refunded|failed
    refunded: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Optional["Order"]] = relationship(back_populates="payment")


class CreditTransaction(Base):
    """Ledger of credit grants/consumption. Positive = grant, negative = spend."""
    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # +1 grant, -1 spend
    reason: Mapped[str] = mapped_column(String(48))  # referral_reward|order_use|admin_grant|...
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    balance_after: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="credit_transactions")


class EmojiPack(Base):
    """A Telegram sticker/emoji set created for a user."""
    __tablename__ = "emoji_packs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    pack_kind: Mapped[str] = mapped_column(String(16))  # emoji|sticker
    nick: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(128))
    # Telegram sticker-set short name (globally unique on Telegram side).
    set_name: Mapped[str] = mapped_column(String(128), index=True)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("pack_kind", "nick", "owner_id", name="uq_pack_kind_nick_owner"),
    )

    items: Mapped[list["PackItem"]] = relationship(back_populates="pack")
    orders: Mapped[list["Order"]] = relationship(back_populates="pack")

    @property
    def telegram_url(self) -> str:
        base = "addemoji" if self.pack_kind == "emoji" else "addstickers"
        return f"https://t.me/{base}/{self.set_name}"


class PackItem(Base):
    __tablename__ = "pack_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pack_id: Mapped[int] = mapped_column(ForeignKey("emoji_packs.id"), index=True)
    template_ref: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pack: Mapped["EmojiPack"] = relationship(back_populates="items")


class Referral(Base):
    """Who invited whom. First referrer only; self-referral rejected."""
    __tablename__ = "referrals"

    referred_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    referrer_id: Mapped[int] = mapped_column(BigInteger, index=True)
    rewarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rewarded_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class RequiredChannel(Base):
    """Mandatory subscription channels, configurable by admin."""
    __tablename__ = "required_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128))  # stored as @name
    title: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Setting(Base):
    """Generic key/value settings (support_contact, etc.)."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    message_type: Mapped[str] = mapped_column(String(16), default="text")  # text|photo|video
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="draft")  # draft|running|done|failed
    target_count: Mapped[int] = mapped_column(Integer, default=0)
    delivered: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payments.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    charge_id: Mapped[str] = mapped_column(String(128))
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="pending")  # pending|done|failed
    admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    done_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
