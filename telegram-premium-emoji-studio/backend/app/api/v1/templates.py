"""Template gallery + font catalog endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models import User
from app.schemas import FontItem, TemplateListResponse
from app.services import catalog_service

router = APIRouter(tags=["catalog"])


@router.get("/templates/{kind}", response_model=TemplateListResponse)
async def list_templates(
    kind: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    _: User = Depends(get_current_user),
):
    data = catalog_service.list_templates(kind, page=page, page_size=page_size)
    return TemplateListResponse(**data)


@router.get("/templates/{kind}/count")
async def template_count(kind: str, _: User = Depends(get_current_user)):
    if kind == "name":
        return {"kind": kind, "total": catalog_service.name_template_count()}
    section = "logo" if kind == "pf" else kind
    return {"kind": kind, "total": catalog_service.logo_template_count(section)}


@router.get("/fonts", response_model=list[FontItem])
async def list_fonts(
    profile: bool = Query(False, description="Profil foni shriftlari"),
    _: User = Depends(get_current_user),
):
    return [FontItem(**f) for f in catalog_service.list_fonts(profile=profile)]
