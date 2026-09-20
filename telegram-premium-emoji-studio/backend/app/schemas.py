"""Pydantic schemas (API request/response models).

Includes strict validators for the security-sensitive inputs the original
engine cared about: HEX colors, template ids/selections, text length.
"""
from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")
PRODUCT_KINDS = ("name", "logo", "logo2", "logo3", "pf")
PACK_KINDS = ("emoji", "sticker")


def normalize_hex(value: Optional[str]) -> Optional[str]:
    """Return a canonical ``#RRGGBB`` string or None if empty. Raises on bad."""
    if value is None:
        return None
    v = value.strip()
    if v == "":
        return None
    m = HEX_RE.match(v)
    if not m:
        raise ValueError("HEX rang noto'g'ri (masalan: #FF0000)")
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h.upper()


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
class AuthRequest(BaseModel):
    init_data: str = Field(..., description="Raw Telegram WebApp initData string")


class UserPublic(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str = ""
    language: str = "uz"
    is_premium: bool = False
    photo_url: Optional[str] = None
    credits: int = 0
    free_access: bool = False
    is_admin: bool = False
    packs_created: int = 0
    stars_spent: int = 0


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


# --------------------------------------------------------------------------
# Templates & fonts
# --------------------------------------------------------------------------
class TemplateItem(BaseModel):
    id: str  # for name: template key; for logo: zero-padded number "001"
    number: Optional[int] = None
    label: str
    kind: str
    custom_emoji_id: Optional[str] = None


class TemplateListResponse(BaseModel):
    kind: str
    total: int
    page: int
    page_size: int
    items: list[TemplateItem]


class FontItem(BaseModel):
    key: str
    label: str


# --------------------------------------------------------------------------
# Rendering / preview
# --------------------------------------------------------------------------
class PreviewRequest(BaseModel):
    kind: Literal["name", "logo", "logo2", "logo3", "pf"]
    text: str = Field(..., min_length=1, max_length=64)
    template: str = Field(..., description="Template key (name) or number (logo/pf)")
    outer_hex: Optional[str] = None
    inner_hex: Optional[str] = None
    # For name: text color. For logo/pf: logo color. Both skippable.
    color_hex: Optional[str] = None
    font_key: Optional[str] = None

    @field_validator("outer_hex", "inner_hex", "color_hex")
    @classmethod
    def _hex(cls, v):
        return normalize_hex(v)

    @field_validator("text")
    @classmethod
    def _text(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("Matn bo'sh bo'lmasligi kerak")
        return v


class PreviewResponse(BaseModel):
    # Lottie animation JSON (renderable in the browser via lottie-web).
    lottie: dict[str, Any]
    kind: str
    template: str
    watermark: bool = False


# --------------------------------------------------------------------------
# Orders
# --------------------------------------------------------------------------
class OrderCreateRequest(BaseModel):
    kind: Literal["name", "logo", "logo2", "logo3", "pf"]
    pack_kind: Literal["emoji", "sticker"] = "emoji"
    text: str = Field(..., min_length=1, max_length=64)
    # Template selection: single "005", list "1,5,8", or "all".
    templates: str = Field(...)
    outer_hex: Optional[str] = None
    inner_hex: Optional[str] = None
    color_hex: Optional[str] = None
    font_key: Optional[str] = None
    pack_title: str = Field(default="", max_length=64)
    # For pf: whether to add to existing pack.
    existing_pack_nick: Optional[str] = None
    idempotency_key: Optional[str] = Field(default=None, max_length=64)

    @field_validator("outer_hex", "inner_hex", "color_hex")
    @classmethod
    def _hex(cls, v):
        return normalize_hex(v)


class OrderPublic(BaseModel):
    id: int
    kind: str
    pack_kind: str
    template_selection: str
    item_count: int
    unit_price: int
    total_price: int
    payment_method: Optional[str]
    status: str
    pack_url: Optional[str] = None
    pack_title: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None


class OrderCheckoutResponse(BaseModel):
    order_id: int
    unit_price: int
    total_price: int
    item_count: int
    currency: str = "XTR"
    # Options offered to the user before paying.
    can_use_credit: bool
    credits_available: int
    is_free_user: bool
    # invoice_link is produced server-side via Bot API (createInvoiceLink).
    invoice_link: Optional[str] = None


class PayWithCreditRequest(BaseModel):
    order_id: int


# --------------------------------------------------------------------------
# Credits / referrals / settings
# --------------------------------------------------------------------------
class CreditBalance(BaseModel):
    credits: int
    transactions: list["CreditTxnPublic"] = []


class CreditTxnPublic(BaseModel):
    amount: int
    reason: str
    balance_after: int
    created_at: Optional[str] = None


class ReferralInfo(BaseModel):
    link: str
    invited_count: int
    successful_count: int
    earned_credits: int


class SettingsPublic(BaseModel):
    support_contact: str
    required_channels: list["ChannelPublic"] = []
    prices: dict[str, int] = {}
    gift_min_amount: int
    gift_max_amount: int
    name_max_len: int
    pf_max_len: int


class ChannelPublic(BaseModel):
    id: int
    username: str
    title: Optional[str] = None
    enabled: bool = True
    url: str = ""


class SubscriptionStatus(BaseModel):
    subscribed: bool
    channels: list[ChannelPublic] = []


# --------------------------------------------------------------------------
# Gift
# --------------------------------------------------------------------------
class GiftRequest(BaseModel):
    amount: int = Field(..., ge=1)


class GiftResponse(BaseModel):
    invoice_link: Optional[str] = None
    amount: int


# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------
class AdminOverview(BaseModel):
    total_users: int
    active_users_7d: int
    total_generations: int
    total_packs: int
    stars_revenue: int
    credits_consumed: int
    recent_orders: list[OrderPublic] = []


class AdminUserRow(BaseModel):
    id: int
    username: Optional[str]
    created_at: Optional[str]
    packs_created: int
    stars_spent: int
    credits: int
    free_access: bool


class PriceUpdate(BaseModel):
    kind: Literal["name", "logo", "logo2", "logo3", "pf", "code"]
    stars: int = Field(..., ge=1, le=1_000_000)


class ChannelCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=128)
    title: Optional[str] = None

    @field_validator("username")
    @classmethod
    def _norm(cls, v):
        v = v.strip()
        if not v.startswith("@"):
            v = "@" + v.lstrip("@")
        if not re.match(r"^@[A-Za-z0-9_]{3,64}$", v):
            raise ValueError("Kanal useri noto'g'ri (masalan: @mychannel)")
        return v


class SupportUpdate(BaseModel):
    contact: str = Field(..., min_length=1, max_length=128)


class FreeAccessUpdate(BaseModel):
    user_id: int
    grant: bool = True


class BroadcastCreate(BaseModel):
    message_type: Literal["text", "photo", "video"] = "text"
    text: Optional[str] = None
    media_file_id: Optional[str] = None


class RefundAction(BaseModel):
    refund_id: int


CreditBalance.model_rebuild()
SettingsPublic.model_rebuild()
