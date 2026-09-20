"""Pricing — reads/writes ProductPrice rows. Prices ALWAYS come from the DB
(never hardcoded in the frontend). Falls back to config defaults when a row is
missing, seeding it on first read.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import ProductPrice

ALL_KINDS = ("name", "logo", "logo2", "logo3", "pf", "code")


def _default_for(kind: str) -> int:
    if kind == "code":
        return settings.default_code_price_stars
    if kind == "pf":
        return settings.default_pf_price_stars
    return settings.default_price_stars


async def get_price(session: AsyncSession, kind: str) -> int:
    row = await session.get(ProductPrice, kind)
    if row is None:
        default = _default_for(kind)
        row = ProductPrice(kind=kind, stars=default)
        session.add(row)
        await session.flush()
        return default
    return int(row.stars)


async def set_price(session: AsyncSession, kind: str, stars: int) -> int:
    row = await session.get(ProductPrice, kind)
    if row is None:
        row = ProductPrice(kind=kind, stars=stars)
        session.add(row)
    else:
        row.stars = stars
    await session.flush()
    return stars


async def all_prices(session: AsyncSession) -> dict[str, int]:
    rows = (await session.execute(select(ProductPrice))).scalars().all()
    existing = {r.kind: int(r.stars) for r in rows}
    # Ensure every kind is present (seed defaults for missing).
    for kind in ALL_KINDS:
        if kind not in existing:
            existing[kind] = await get_price(session, kind)
    return existing
