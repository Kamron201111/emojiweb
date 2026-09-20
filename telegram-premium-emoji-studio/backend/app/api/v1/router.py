"""Aggregate all v1 routers under a single APIRouter."""
from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    me,
    orders,
    payments,
    referrals,
    render,
    settings,
    templates,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(templates.router)
api_router.include_router(render.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
api_router.include_router(referrals.router)
api_router.include_router(settings.router)
api_router.include_router(admin.router)
