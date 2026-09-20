"""Application configuration loaded from environment variables (.env).

Secrets (BOT_TOKEN, SECRET_KEY, ...) are NEVER hardcoded and NEVER exposed to
the frontend. See .env.example for the full list of settings.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../app
BACKEND_DIR = os.path.dirname(BASE_DIR)  # .../backend
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BACKEND_DIR, "data")


class Settings(BaseSettings):
    """Central settings object.

    All values come from environment variables (or an .env file). No secret has
    a real default — deployments must provide their own.
    """

    model_config = SettingsConfigDict(
        env_file=os.path.join(BACKEND_DIR, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Core / app ---------------------------------------------------------
    app_name: str = "Telegram Premium Emoji Studio"
    environment: str = Field(default="development")  # development | production
    debug: bool = Field(default=False)
    api_prefix: str = "/api/v1"

    # --- Telegram -----------------------------------------------------------
    # BOT_TOKEN is REQUIRED at runtime. It is used only server-side to validate
    # initData and to call the Bot API. It is never sent to the frontend.
    bot_token: str = Field(default="")
    bot_username: str = Field(default="")
    # Comma-separated list of admin Telegram user IDs, e.g. "111,222".
    admin_ids: str = Field(default="")
    log_chat_id: int = Field(default=0)
    # Public URL where the Mini App is hosted (used to build referral links).
    webapp_url: str = Field(default="http://localhost:5173")

    # --- Security -----------------------------------------------------------
    secret_key: str = Field(default="CHANGE_ME_INSECURE_DEV_KEY")
    # How long a validated initData session token is considered fresh (seconds).
    auth_ttl_seconds: int = Field(default=86400)
    # Max age of Telegram initData auth_date we accept (seconds). 24h default.
    initdata_max_age_seconds: int = Field(default=86400)

    # --- Database -----------------------------------------------------------
    database_url: str = Field(
        default="sqlite+aiosqlite:///" + os.path.join(DATA_DIR, "app.db")
    )

    # --- CORS ---------------------------------------------------------------
    # Comma-separated list of allowed origins for the frontend.
    cors_origins: str = Field(default="*")

    # --- Rendering ----------------------------------------------------------
    render_tmp_dir: str = Field(default=os.path.join(DATA_DIR, "render_tmp"))
    render_max_concurrency: int = Field(default=2)
    preview_watermark: bool = Field(default=True)

    # --- Rate limiting ------------------------------------------------------
    rate_limit_preview_per_min: int = Field(default=20)
    rate_limit_default_per_min: int = Field(default=120)

    # --- Business defaults (used when a price row is missing) ---------------
    default_price_stars: int = Field(default=15)
    default_code_price_stars: int = Field(default=5000)
    default_pf_price_stars: int = Field(default=10)
    default_support_contact: str = Field(default="@your_support_username")
    gift_min_amount: int = Field(default=1)
    gift_max_amount: int = Field(default=100000)

    # --- Text limits (mirror the original engine constraints) ---------------
    name_max_len: int = Field(default=12)
    pf_max_len: int = Field(default=5)
    logo_page_size: int = Field(default=10)

    @field_validator("environment")
    @classmethod
    def _normalize_env(cls, v: str) -> str:
        return (v or "development").strip().lower()

    @property
    def admin_id_list(self) -> List[int]:
        out: List[int] = []
        for part in (self.admin_ids or "").replace(";", ",").split(","):
            part = part.strip()
            if part.lstrip("-").isdigit():
                out.append(int(part))
        return out

    @property
    def cors_origin_list(self) -> List[str]:
        raw = (self.cors_origins or "").strip()
        if raw in ("", "*"):
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_id_list


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Ensure runtime directories exist.
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(settings.render_tmp_dir, exist_ok=True)
