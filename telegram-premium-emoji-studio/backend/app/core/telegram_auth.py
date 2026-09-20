"""Telegram Mini App initData cryptographic validation.

The frontend sends the raw ``initData`` query string produced by
``window.Telegram.WebApp.initData``. We MUST verify it server-side using the
bot token before trusting any field (especially the user id). We NEVER trust a
user id supplied directly by the client.

Algorithm (per Telegram docs):
    secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
    data_check_string = "\n".join(sorted "key=value" pairs, excluding hash)
    calculated_hash = hex(HMAC_SHA256(key=secret_key, msg=data_check_string))
    valid <=> calculated_hash == provided hash
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl


class InitDataError(Exception):
    """Raised when initData is missing, malformed, tampered, or expired."""


@dataclass
class TelegramUser:
    id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    language_code: str = ""
    is_premium: bool = False
    photo_url: str = ""

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.first_name, self.last_name) if p).strip()


@dataclass
class InitData:
    user: TelegramUser
    auth_date: int
    query_id: str = ""
    start_param: str = ""
    raw: str = ""


def _build_secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 86400,
) -> InitData:
    """Validate a Telegram Mini App initData string.

    Returns a parsed :class:`InitData` on success. Raises :class:`InitDataError`
    on any failure (missing hash, bad signature, expired, no user).
    """
    if not init_data:
        raise InitDataError("initData bo'sh")
    if not bot_token:
        raise InitDataError("BOT_TOKEN sozlanmagan")

    # parse_qsl keeps order but we need to separate the hash.
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("hash topilmadi")

    # Build the data-check-string from the remaining, sorted key=value pairs.
    data_check_string = "\n".join(
        f"{k}={pairs[k]}" for k in sorted(pairs.keys())
    )

    secret_key = _build_secret_key(bot_token)
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise InitDataError("initData imzosi noto'g'ri (tekshiruvdan o'tmadi)")

    # Expiry check.
    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except (TypeError, ValueError):
        raise InitDataError("auth_date noto'g'ri")

    if max_age_seconds > 0 and auth_date > 0:
        age = int(time.time()) - auth_date
        if age > max_age_seconds:
            raise InitDataError("initData muddati o'tgan")

    # User is required.
    user_raw = pairs.get("user")
    if not user_raw:
        raise InitDataError("foydalanuvchi ma'lumoti yo'q")
    try:
        u = json.loads(user_raw)
    except json.JSONDecodeError:
        raise InitDataError("foydalanuvchi ma'lumoti buzilgan")

    if "id" not in u:
        raise InitDataError("foydalanuvchi id yo'q")

    user = TelegramUser(
        id=int(u["id"]),
        first_name=str(u.get("first_name", "")),
        last_name=str(u.get("last_name", "")),
        username=str(u.get("username", "")),
        language_code=str(u.get("language_code", "")),
        is_premium=bool(u.get("is_premium", False)),
        photo_url=str(u.get("photo_url", "")),
    )

    return InitData(
        user=user,
        auth_date=auth_date,
        query_id=pairs.get("query_id", ""),
        start_param=pairs.get("start_param", ""),
        raw=init_data,
    )


def safe_parse_user(init_data: str, bot_token: str, **kw) -> Optional[TelegramUser]:
    """Convenience: return the validated user or ``None`` (never raises)."""
    try:
        return validate_init_data(init_data, bot_token, **kw).user
    except InitDataError:
        return None
