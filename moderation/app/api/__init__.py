# app/api/__init__.py
from fastapi import APIRouter

from app.api.moderation import router as moderation_router
from app.api.auth import router as auth_router
from app.api.moderators import router as moderators_router

router = APIRouter(prefix="/api/v1")

# По канону: без лишних префиксов
router.include_router(auth_router, prefix="", tags=["Auth"])
router.include_router(moderators_router, prefix="", tags=["Moderators"])
router.include_router(moderation_router, prefix="", tags=["Moderation"])