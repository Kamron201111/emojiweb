"""Idempotent migration of the original bot's flat JSON stores into the new DB.

Reads (if present) from a source directory:
    users.json           -> User rows
    user_languages.json  -> User.language
    stats.json           -> User.packs_created / stars_spent / username
    credits.json         -> User.credits (+ CreditTransaction seed)
    allowed_users.json   -> User.free_access
    referrals.json       -> Referral rows
    settings.json        -> support_contact + RequiredChannel rows
    price_*.json         -> ProductPrice rows
    emoji_pack.json      -> EmojiPack rows (best-effort; keys are kind:nick:owner)

Running it multiple times is safe: rows are upserted, never duplicated, and the
original files are never modified.
"""
from __future__ import annotations

import json
import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CreditTransaction,
    EmojiPack,
    ProductPrice,
    Referral,
    RequiredChannel,
    Setting,
    User,
)


def _load(path: str) -> Any:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


async def _ensure_user(session: AsyncSession, uid: int) -> User:
    user = await session.get(User, uid)
    if user is None:
        user = User(id=uid, language="uz")
        session.add(user)
        await session.flush()
    return user


async def migrate(session: AsyncSession, src_dir: str) -> dict:
    report: dict[str, int] = {
        "users": 0, "languages": 0, "credits": 0, "free_access": 0,
        "referrals": 0, "channels": 0, "prices": 0, "packs": 0, "stats": 0,
    }

    # users.json -> [ids]
    users = _load(os.path.join(src_dir, "users.json")) or []
    for uid in users:
        await _ensure_user(session, int(uid))
        report["users"] += 1

    # user_languages.json -> {uid: lang}
    langs = _load(os.path.join(src_dir, "user_languages.json")) or {}
    for uid, lang in langs.items():
        u = await _ensure_user(session, int(uid))
        if lang in ("uz", "ru", "en"):
            u.language = lang
            report["languages"] += 1

    # stats.json -> {uid: {packs, stars, username}}
    stats = _load(os.path.join(src_dir, "stats.json")) or {}
    for uid, entry in stats.items():
        u = await _ensure_user(session, int(uid))
        u.packs_created = int(entry.get("packs", 0))
        u.stars_spent = int(entry.get("stars", 0))
        if entry.get("username"):
            u.username = entry["username"]
        report["stats"] += 1

    # credits.json -> {uid: int}
    credits = _load(os.path.join(src_dir, "credits.json")) or {}
    for uid, bal in credits.items():
        u = await _ensure_user(session, int(uid))
        bal = int(bal)
        if u.credits != bal:
            delta = bal - u.credits
            u.credits = bal
            if delta:
                session.add(CreditTransaction(
                    user_id=u.id, amount=delta, reason="migration", balance_after=bal,
                ))
            report["credits"] += 1

    # allowed_users.json -> [ids]
    allowed = _load(os.path.join(src_dir, "allowed_users.json")) or []
    for uid in allowed:
        u = await _ensure_user(session, int(uid))
        u.free_access = True
        report["free_access"] += 1

    # referrals.json -> {referred: {referrer, rewarded}}
    referrals = _load(os.path.join(src_dir, "referrals.json")) or {}
    for referred, entry in referrals.items():
        rid = int(referred)
        if await session.get(Referral, rid) is None:
            session.add(Referral(
                referred_id=rid, referrer_id=int(entry.get("referrer", 0)),
                rewarded=bool(entry.get("rewarded", False)),
            ))
            report["referrals"] += 1

    # settings.json -> channels + support_contact
    settings_json = _load(os.path.join(src_dir, "settings.json")) or {}
    support = settings_json.get("support_contact")
    if support:
        row = await session.get(Setting, "support_contact")
        if row is None:
            session.add(Setting(key="support_contact", value=support))
        else:
            row.value = support
    channels = settings_json.get("channels") or (
        [settings_json["channel"]] if settings_json.get("channel") else []
    )
    existing_ch = {c.username for c in (await _all_channels(session))}
    for ch in channels:
        uname = ch if str(ch).startswith("@") else f"@{str(ch).lstrip('@')}"
        if uname not in existing_ch:
            session.add(RequiredChannel(username=uname, enabled=True))
            report["channels"] += 1

    # price_*.json -> ProductPrice
    price_files = {
        "name": "price_name.json", "logo": "price_logo.json",
        "logo2": "price_logo2.json", "logo3": "price_logo3.json",
        "pf": "price_pf.json", "code": "price_code.json",
    }
    for kind, fname in price_files.items():
        data = _load(os.path.join(src_dir, fname))
        if data and "stars" in data:
            row = await session.get(ProductPrice, kind)
            if row is None:
                session.add(ProductPrice(kind=kind, stars=int(data["stars"])))
            else:
                row.stars = int(data["stars"])
            report["prices"] += 1

    # emoji_pack.json -> {kind:nick:owner: set_name}
    packs = _load(os.path.join(src_dir, "emoji_pack.json")) or {}
    for key, set_name in packs.items():
        parts = key.split(":")
        if len(parts) != 3:
            continue
        pack_kind, nick, owner = parts
        try:
            owner_id = int(owner)
        except ValueError:
            continue
        await _ensure_user(session, owner_id)
        exists = await _find_pack(session, owner_id, pack_kind, nick)
        if exists is None:
            session.add(EmojiPack(
                owner_id=owner_id, pack_kind=pack_kind, nick=nick,
                title=nick, set_name=set_name, item_count=0,
            ))
            report["packs"] += 1

    await session.commit()
    return report


async def _all_channels(session: AsyncSession):
    from sqlalchemy import select
    return (await session.execute(select(RequiredChannel))).scalars().all()


async def _find_pack(session: AsyncSession, owner_id: int, pack_kind: str, nick: str):
    from sqlalchemy import select
    stmt = select(EmojiPack).where(
        EmojiPack.owner_id == owner_id,
        EmojiPack.pack_kind == pack_kind,
        EmojiPack.nick == nick,
    )
    return (await session.execute(stmt)).scalar_one_or_none()
