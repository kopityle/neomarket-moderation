from fastapi import APIRouter

from app.api.moderation import router as moderation_router
from app.api.internal import router as internal_router

router = APIRouter(prefix="/api/v1")

router.include_router(moderation_router, prefix="/product-moderation", tags=["Product Moderation"])
router.include_router(internal_router, prefix="/internal", tags=["Internal"])