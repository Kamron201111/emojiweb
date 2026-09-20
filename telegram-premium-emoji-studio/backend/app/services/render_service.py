"""Rendering service — a clean wrapper around the preserved engine logic.

This reuses the original, working rendering algorithms (Lottie/TGS
manipulation, SVG path parsing, text-to-vector, recoloring, template
placeholder positioning) extracted into ``app.renderers`` WITHOUT simplifying
them. It exposes two outputs:

    * ``render_lottie(...)``  -> a Lottie dict for the browser live preview
    * ``render_tgs(...)``     -> gzipped .tgs bytes for Telegram pack creation

Rendering is CPU-bound; callers should run these via a bounded thread pool /
semaphore (see PreviewService / order generation) so one expensive render can't
block the whole event loop.
"""
from __future__ import annotations

import gzip
import io
import json
import os
from typing import Any, Optional

from app.core.config import ASSETS_DIR
from app.renderers import logo_engine, template_engine
from app.renderers.templates_config import TEMPLATES

# Directory mapping for the three logo/extra sections.
LOGO_DIRS = {
    "logo": os.path.join(ASSETS_DIR, "templates_tgs"),
    "logo2": os.path.join(ASSETS_DIR, "templates_tgs2"),
    "logo3": os.path.join(ASSETS_DIR, "templates_tgs3"),
}

DEFAULT_SIZE_PERCENT = getattr(logo_engine, "DEFAULT_SIZE_PERCENT", 135)

# Profile-background default colors (as in the original engine).
PF_DEFAULT_OUTER = "#1f2937"
PF_DEFAULT_INNER = "#374151"
PF_DEFAULT_LOGO = "#FFFFFF"
PF_DEFAULT_TEMPLATE = "002.json"


class RenderError(Exception):
    """Raised on any rendering failure with an Uzbek-safe message."""


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _tgs_bytes_to_lottie(tgs_bytes: bytes) -> dict[str, Any]:
    """Decompress .tgs (gzipped Lottie JSON) into a plain Lottie dict."""
    with gzip.open(io.BytesIO(tgs_bytes), "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def _lottie_to_tgs_bytes(lottie: dict[str, Any]) -> bytes:
    raw = json.dumps(lottie, separators=(",", ":")).encode("utf-8")
    buf = io.BytesIO()
    with gzip.open(buf, "wb") as f:
        f.write(raw)
    return buf.getvalue()


def _resolve_logo_template_filename(template: str) -> str:
    """Accept "5", "005" or "005.json" -> "005.json"."""
    t = str(template).strip()
    if t.endswith(".json"):
        t = t[:-5]
    if not t.isdigit():
        raise RenderError("Shablon raqami noto'g'ri")
    return f"{int(t):03d}.json"


def font_path_for(font_key: Optional[str], *, profile: bool = False) -> str:
    """Resolve a font key to an absolute path, never exposing paths to users."""
    options = logo_engine.PROFILE_FONT_OPTIONS if profile else logo_engine.FONT_OPTIONS
    if font_key and font_key in options:
        return options[font_key][1]
    # Sensible defaults matching the original engine.
    if profile:
        return logo_engine.PROFILE_FONT_OPTIONS["archivo"][1]
    return logo_engine.FONT_OPTIONS["classic"][1]


# --------------------------------------------------------------------------
# Name emoji
# --------------------------------------------------------------------------
def render_name_lottie(
    template_key: str,
    word: str,
    outer_hex: Optional[str],
    inner_hex: Optional[str],
    text_hex: Optional[str],
) -> dict[str, Any]:
    if template_key not in TEMPLATES:
        raise RenderError("Bunday Name shabloni yo'q")
    cfg = TEMPLATES[template_key]
    try:
        return template_engine.render_template(
            cfg, word, outer_hex=outer_hex, inner_hex=inner_hex, text_hex=text_hex
        )
    except Exception as e:  # noqa: BLE001 - convert to domain error
        raise RenderError(f"Name emoji yasab bo'lmadi: {e}") from e


def render_name_tgs(*args, **kwargs) -> bytes:
    return _lottie_to_tgs_bytes(render_name_lottie(*args, **kwargs))


# --------------------------------------------------------------------------
# Logo / Extra emoji (logo, logo2, logo3)
# --------------------------------------------------------------------------
def render_logo_tgs(
    kind: str,
    template: str,
    text: str,
    outer_hex: str,
    inner_hex: str,
    logo_hex: Optional[str],
    font_key: Optional[str] = None,
    size_percent: int = DEFAULT_SIZE_PERCENT,
) -> bytes:
    if kind not in LOGO_DIRS:
        raise RenderError("Bunday bo'lim yo'q")
    dir_path = LOGO_DIRS[kind]
    filename = _resolve_logo_template_filename(template)
    font_path = font_path_for(font_key)
    try:
        svg = logo_engine.text_to_svg(text, font_path=font_path)
        tgs_bytes, _ = logo_engine.build_tgs_sticker(
            filename,
            svg,
            outer_hex or "#000000",
            inner_hex or "#000000",
            logo_hex or logo_engine.DEFAULT_LOGO_COLOR,
            size_percent=size_percent,
            dir_path=dir_path,
        )
        return tgs_bytes
    except Exception as e:  # noqa: BLE001
        raise RenderError(f"Logo emoji yasab bo'lmadi: {e}") from e


def render_logo_lottie(*args, **kwargs) -> dict[str, Any]:
    return _tgs_bytes_to_lottie(render_logo_tgs(*args, **kwargs))


# --------------------------------------------------------------------------
# Profile background (pf)
# --------------------------------------------------------------------------
def render_pf_tgs(
    template: str,
    text: str,
    outer_hex: Optional[str],
    inner_hex: Optional[str],
    logo_hex: Optional[str],
    font_key: Optional[str] = None,
    size_percent: int = DEFAULT_SIZE_PERCENT,
) -> bytes:
    filename = _resolve_logo_template_filename(template or PF_DEFAULT_TEMPLATE)
    font_path = font_path_for(font_key, profile=True)
    try:
        svg = logo_engine.text_to_svg(text, font_path=font_path)
        tgs_bytes, _ = logo_engine.build_tgs_sticker(
            filename,
            svg,
            outer_hex or PF_DEFAULT_OUTER,
            inner_hex or PF_DEFAULT_INNER,
            logo_hex or PF_DEFAULT_LOGO,
            size_percent=size_percent,
            dir_path=LOGO_DIRS["logo"],
        )
        return tgs_bytes
    except Exception as e:  # noqa: BLE001
        raise RenderError(f"Profil foni yasab bo'lmadi: {e}") from e


def render_pf_lottie(*args, **kwargs) -> dict[str, Any]:
    return _tgs_bytes_to_lottie(render_pf_tgs(*args, **kwargs))


# --------------------------------------------------------------------------
# Unified dispatch used by preview + order generation
# --------------------------------------------------------------------------
def render_lottie(
    kind: str,
    template: str,
    text: str,
    outer_hex: Optional[str],
    inner_hex: Optional[str],
    color_hex: Optional[str],
    font_key: Optional[str] = None,
) -> dict[str, Any]:
    if kind == "name":
        return render_name_lottie(template, text, outer_hex, inner_hex, color_hex)
    if kind in ("logo", "logo2", "logo3"):
        return render_logo_lottie(
            kind, template, text, outer_hex, inner_hex, color_hex, font_key
        )
    if kind == "pf":
        return render_pf_lottie(template, text, outer_hex, inner_hex, color_hex, font_key)
    raise RenderError("Noma'lum tur")


def render_tgs(
    kind: str,
    template: str,
    text: str,
    outer_hex: Optional[str],
    inner_hex: Optional[str],
    color_hex: Optional[str],
    font_key: Optional[str] = None,
) -> bytes:
    if kind == "name":
        return render_name_tgs(template, text, outer_hex, inner_hex, color_hex)
    if kind in ("logo", "logo2", "logo3"):
        return render_logo_tgs(
            kind, template, text, outer_hex, inner_hex, color_hex, font_key
        )
    if kind == "pf":
        return render_pf_tgs(template, text, outer_hex, inner_hex, color_hex, font_key)
    raise RenderError("Noma'lum tur")
