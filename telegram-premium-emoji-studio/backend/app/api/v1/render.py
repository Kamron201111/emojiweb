"""Live preview endpoint — renders a single template to Lottie for the browser.

Runs the CPU-bound render in a bounded thread pool (semaphore) so one expensive
render can't block the event loop. Rate-limited per user.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import preview_rate_limit
from app.core.config import settings
from app.models import User
from app.schemas import PreviewRequest, PreviewResponse
from app.services import render_service

router = APIRouter(prefix="/render", tags=["render"])

_preview_semaphore = asyncio.Semaphore(settings.render_max_concurrency)


@router.post("/preview", response_model=PreviewResponse)
async def preview(body: PreviewRequest, user: User = Depends(preview_rate_limit)):
    # Enforce text limits per kind (defense in depth beyond schema).
    if body.kind == "name" and len(body.text) > settings.name_max_len:
        raise HTTPException(status_code=422, detail=f"So'z {settings.name_max_len} belgidan oshmasin")
    if body.kind == "pf" and len(body.text) > settings.pf_max_len:
        raise HTTPException(status_code=422, detail=f"Matn {settings.pf_max_len} belgidan oshmasin")

    try:
        async with _preview_semaphore:
            lottie = await asyncio.to_thread(
                render_service.render_lottie,
                body.kind, body.template, body.text,
                body.outer_hex, body.inner_hex, body.color_hex, body.font_key,
            )
    except render_service.RenderError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Render xatosi: {e}") from e

    return PreviewResponse(
        lottie=lottie,
        kind=body.kind,
        template=body.template,
        watermark=settings.preview_watermark,
    )
