# app/api/dependencies.py
from fastapi import Header, HTTPException, status, Depends
from uuid import UUID
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.moderator_service import ModeratorAdminService


async def get_current_moderator_id(
    x_moderator_id: str = Header(..., alias="X-Moderator-Id")
) -> UUID:
    """Получить ID текущего модератора из заголовка"""
    try:
        return UUID(x_moderator_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Moderator-Id format"
        )


async def require_admin(
    current_moderator_id: UUID = Depends(get_current_moderator_id),
    db: Session = Depends(get_db),
) -> bool:
    """Проверить, что текущий пользователь — ADMIN."""
    service = ModeratorAdminService(db)
    moderator = service.get_moderator(current_moderator_id)
    
    if not moderator or moderator.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    
    return True