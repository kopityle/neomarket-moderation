from fastapi import APIRouter

from app.api.moderation import router as moderation_router

router = APIRouter(prefix="/api/v1")

# По канону: без лишних префиксов
router.include_router(moderation_router, prefix="", tags=["Moderation"])