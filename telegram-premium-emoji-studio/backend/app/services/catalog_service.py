"""Template & font catalog — reads the real asset files (never trusts a
hardcoded count) and exposes them with preview custom-emoji ids.
"""
from __future__ import annotations

import functools
import os

from app.core.config import ASSETS_DIR
from app.renderers.logo_emoji_ids import (
    LOGO2_TEMPLATE_EMOJI_IDS,
    LOGO3_TEMPLATE_EMOJI_IDS,
    LOGO_TEMPLATE_EMOJI_IDS,
)
from app.renderers import logo_engine
from app.renderers.templates_config import EMOJI_IDS, TEMPLATE_ORDER, TEMPLATES

LOGO_DIRS = {
    "logo": os.path.join(ASSETS_DIR, "templates_tgs"),
    "logo2": os.path.join(ASSETS_DIR, "templates_tgs2"),
    "logo3": os.path.join(ASSETS_DIR, "templates_tgs3"),
}
LOGO_EMOJI_MAPS = {
    "logo": LOGO_TEMPLATE_EMOJI_IDS,
    "logo2": LOGO2_TEMPLATE_EMOJI_IDS,
    "logo3": LOGO3_TEMPLATE_EMOJI_IDS,
}

SECTION_TITLES = {
    "name": {"uz": "Name Emojis", "ru": "Name Emojis", "en": "Name Emojis"},
    "logo": {"uz": "Logo/Text Emojis", "ru": "Logo/Text Emojis", "en": "Logo/Text Emojis"},
    "logo2": {"uz": "Extra Emojis (Bo'lim 3)", "ru": "Extra Emojis (Раздел 3)", "en": "Extra Emojis (Section 3)"},
    "logo3": {"uz": "Extra Emojis (Bo'lim 4)", "ru": "Extra Emojis (Раздел 4)", "en": "Extra Emojis (Section 4)"},
    "pf": {"uz": "Profil foni", "ru": "Фон профиля", "en": "Profile Background"},
}


@functools.lru_cache(maxsize=8)
def _count_logo_templates(kind: str) -> int:
    d = LOGO_DIRS.get(kind)
    if not d or not os.path.isdir(d):
        return 0
    return len([f for f in os.listdir(d) if f.endswith(".json")])


def logo_template_count(kind: str) -> int:
    return _count_logo_templates(kind)


def name_template_count() -> int:
    return len(TEMPLATES)


def list_fonts(profile: bool = False) -> list[dict]:
    options = logo_engine.PROFILE_FONT_OPTIONS if profile else logo_engine.FONT_OPTIONS
    return [{"key": k, "label": label} for k, (label, _p) in options.items()]


def name_template_keys() -> list[str]:
    """Curated order first (TEMPLATE_ORDER), then any remaining TEMPLATES keys.

    The original bot only exposed the 15 curated templates via TEMPLATE_ORDER,
    but the repo ships 28 renderable templates. The Mini App surfaces all of
    them, keeping the curated ones up front.
    """
    ordered = [k for k in TEMPLATE_ORDER if k in TEMPLATES]
    rest = [k for k in TEMPLATES.keys() if k not in ordered]
    return ordered + rest


def _name_items() -> list[dict]:
    items = []
    for key in name_template_keys():
        cfg = TEMPLATES.get(key, {})
        items.append(
            {
                "id": key,
                "number": None,
                "label": cfg.get("label", key),
                "kind": "name",
                "custom_emoji_id": (EMOJI_IDS.get(key) if isinstance(EMOJI_IDS, dict) else None),
            }
        )
    return items


def _logo_items(kind: str) -> list[dict]:
    total = _count_logo_templates(kind)
    emap = LOGO_EMOJI_MAPS.get(kind, {})
    items = []
    for n in range(1, total + 1):
        items.append(
            {
                "id": f"{n:03d}",
                "number": n,
                "label": f"{n}-shablon",
                "kind": kind,
                "custom_emoji_id": emap.get(n),
            }
        )
    return items


def list_templates(kind: str, page: int = 1, page_size: int = 24) -> dict:
    """Return a paginated list of templates for a section."""
    if kind == "name":
        all_items = _name_items()
    elif kind in ("logo", "logo2", "logo3", "pf"):
        # pf browses the primary logo templates.
        section = "logo" if kind == "pf" else kind
        all_items = _logo_items(section)
    else:
        all_items = []

    total = len(all_items)
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "kind": kind,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": all_items[start:end],
    }


def section_title(kind: str, lang: str = "uz") -> str:
    return SECTION_TITLES.get(kind, {}).get(lang, SECTION_TITLES.get(kind, {}).get("uz", kind))


def validate_template_selection(kind: str, selection: str) -> list[str]:
    """Parse and validate a template selection string.

    Accepts: single ("005"), delimited ("1,5,8" / "3.8.1"), ranges ("1-5"),
    or "all". Returns the concrete list of resolved template ids/keys.
    Raises ValueError on anything invalid.
    """
    sel = (selection or "").strip().lower()
    if kind == "name":
        keys = name_template_keys()
        valid = set(keys)
        if sel in ("all", "*", "hammasi"):
            return list(keys)
        chosen = [s.strip() for s in sel.split(",") if s.strip()]
        out = [c for c in chosen if c in valid]
        if not out:
            raise ValueError("Shablon tanlanmadi yoki noto'g'ri")
        return out

    section = "logo" if kind == "pf" else kind
    total = _count_logo_templates(section)
    if total == 0:
        raise ValueError("Bu bo'limda shablon yo'q")
    if sel in ("all", "*", "hammasi"):
        return [f"{n:03d}" for n in range(1, total + 1)]

    numbers: list[int] = []
    for token in sel.replace(".", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            a, _, b = token.partition("-")
            if a.isdigit() and b.isdigit():
                lo, hi = int(a), int(b)
                if lo > hi:
                    lo, hi = hi, lo
                numbers.extend(range(lo, hi + 1))
                continue
        if token.isdigit():
            numbers.append(int(token))
    # de-dup preserve order, bound to range
    seen = set()
    resolved = []
    for n in numbers:
        if 1 <= n <= total and n not in seen:
            seen.add(n)
            resolved.append(f"{n:03d}")
    if not resolved:
        raise ValueError(f"Noto'g'ri shablon raqami (1 dan {total} gacha)")
    return resolved
