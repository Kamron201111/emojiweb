"""Async Telegram Bot API client (httpx).

Wraps only the endpoints this app needs. The BOT_TOKEN is read from settings
and used server-side only; it is never returned to the frontend.

Rate-limit handling: on HTTP 429 the client honors ``retry_after`` and retries,
mirroring the original bot's TelegramRetryAfter loop.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from app.core.config import settings

log = logging.getLogger("telegram")

API_BASE = "https://api.telegram.org"


class TelegramAPIError(Exception):
    def __init__(self, method: str, description: str, error_code: int | None = None):
        self.method = method
        self.description = description
        self.error_code = error_code
        super().__init__(f"{method} failed: {description}")


class BotClient:
    def __init__(self, token: Optional[str] = None, *, timeout: float = 60.0):
        self.token = token or settings.bot_token
        self._timeout = timeout

    @property
    def _url(self) -> str:
        return f"{API_BASE}/bot{self.token}"

    async def _call(self, method: str, *, data=None, files=None, retries: int = 3) -> Any:
        if not self.token:
            raise TelegramAPIError(method, "BOT_TOKEN sozlanmagan")
        url = f"{self._url}/{method}"
        attempt = 0
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while True:
                attempt += 1
                resp = await client.post(url, data=data, files=files)
                payload = {}
                try:
                    payload = resp.json()
                except Exception:  # noqa: BLE001
                    pass
                if resp.status_code == 200 and payload.get("ok"):
                    return payload.get("result")
                # Rate limit
                if resp.status_code == 429 or payload.get("error_code") == 429:
                    retry_after = int(
                        payload.get("parameters", {}).get("retry_after", 1)
                    )
                    if attempt <= retries:
                        await asyncio.sleep(retry_after + 1)
                        continue
                desc = payload.get("description", resp.text)
                raise TelegramAPIError(method, desc, payload.get("error_code"))

    # --- Basic ----------------------------------------------------------
    async def get_me(self) -> dict:
        return await self._call("getMe")

    async def get_chat_member(self, chat_id: str | int, user_id: int) -> dict:
        return await self._call(
            "getChatMember", data={"chat_id": chat_id, "user_id": user_id}
        )

    async def send_message(self, chat_id: int | str, text: str, **kw) -> dict:
        data = {"chat_id": chat_id, "text": text, **kw}
        return await self._call("sendMessage", data=data)

    async def copy_message(self, chat_id: int, from_chat_id: int, message_id: int) -> dict:
        return await self._call(
            "copyMessage",
            data={"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id},
        )

    # --- Payments -------------------------------------------------------
    async def create_invoice_link(
        self, title: str, description: str, payload: str, prices: list[dict],
        currency: str = "XTR",
    ) -> str:
        import json as _json

        return await self._call(
            "createInvoiceLink",
            data={
                "title": title[:32],
                "description": description[:255],
                "payload": payload,
                "provider_token": "",  # empty for Telegram Stars
                "currency": currency,
                "prices": _json.dumps(prices),
            },
        )

    async def answer_pre_checkout_query(self, pre_checkout_query_id: str, ok: bool = True,
                                        error_message: str | None = None) -> bool:
        data: dict[str, Any] = {"pre_checkout_query_id": pre_checkout_query_id, "ok": ok}
        if error_message:
            data["error_message"] = error_message
        return await self._call("answerPreCheckoutQuery", data=data)

    async def refund_star_payment(self, user_id: int, telegram_payment_charge_id: str) -> bool:
        return await self._call(
            "refundStarPayment",
            data={"user_id": user_id, "telegram_payment_charge_id": telegram_payment_charge_id},
        )

    # --- Stickers / packs ----------------------------------------------
    async def create_new_sticker_set(
        self, user_id: int, name: str, title: str, sticker_bytes: bytes,
        sticker_type: str = "custom_emoji", emoji: str = "🙂",
    ) -> bool:
        import json as _json

        files = {"sticker_file": ("sticker.tgs", sticker_bytes, "application/gzip")}
        stickers = [{
            "sticker": "attach://sticker_file",
            "format": "animated",
            "emoji_list": [emoji],
        }]
        data = {
            "user_id": user_id,
            "name": name,
            "title": title,
            "sticker_type": sticker_type,
            "stickers": _json.dumps(stickers),
        }
        return await self._call("createNewStickerSet", data=data, files=files)

    async def add_sticker_to_set(
        self, user_id: int, name: str, sticker_bytes: bytes, emoji: str = "🙂",
    ) -> bool:
        import json as _json

        files = {"sticker_file": ("sticker.tgs", sticker_bytes, "application/gzip")}
        sticker = {
            "sticker": "attach://sticker_file",
            "format": "animated",
            "emoji_list": [emoji],
        }
        data = {"user_id": user_id, "name": name, "sticker": _json.dumps(sticker)}
        return await self._call("addStickerToSet", data=data, files=files)


def get_bot() -> BotClient:
    return BotClient()
