"""CLI: register the Telegram webhook for payment updates.

Usage:
    python -m scripts.set_webhook https://your-domain.com

Sets the webhook to <base>/api/v1/payments/telegram-webhook with a secret
token derived from SECRET_KEY, and subscribes to message + pre_checkout_query.
"""
from __future__ import annotations

import asyncio
import sys

import httpx

from app.core.config import settings


async def _run(base_url: str) -> None:
    if not settings.bot_token:
        print("BOT_TOKEN sozlanmagan (.env)")
        raise SystemExit(1)
    url = f"{base_url.rstrip('/')}{settings.api_prefix}/payments/telegram-webhook"
    secret = settings.secret_key[:32]
    api = f"https://api.telegram.org/bot{settings.bot_token}/setWebhook"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(api, data={
            "url": url,
            "secret_token": secret,
            "allowed_updates": '["message","pre_checkout_query"]',
        })
        print(resp.status_code, resp.text)


def main() -> None:
    if len(sys.argv) < 2:
        print("Foydalanish: python -m scripts.set_webhook <public_base_url>")
        raise SystemExit(1)
    asyncio.run(_run(sys.argv[1]))


if __name__ == "__main__":
    main()
