"""FastAPI application entrypoint for Telegram Premium Emoji Studio."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db

logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (SQLite dev) — production uses Alembic migrations.
    await init_db()
    log.info("Database initialized (%s)", settings.database_url.split("://")[0])
    if not settings.bot_token:
        log.warning("BOT_TOKEN sozlanmagan — Telegram funksiyalari ishlamaydi!")
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "version": __version__, "env": settings.environment}


@app.get("/", tags=["system"])
async def root():
    return JSONResponse({"app": settings.app_name, "version": __version__, "docs": "/docs"})
