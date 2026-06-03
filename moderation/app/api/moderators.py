# app/api/moderators.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from app.database import get_db
from app.services.moderator_service import ModeratorAdminService
from app.schemas.moderator import (
    ModeratorResponse,
    ModeratorCreateRequest,
    ModeratorUpdateRequest,
    PaginatedModerators,
)
from app.api.dependencies import get_current_moderator_id, require_admin

router = APIRouter(tags=["Moderators"])


@router.get("/moderators", response_model=PaginatedModerators)
def list_moderators(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_moderator_id: UUID = Depends(get_current_moderator_id),
    _: bool = Depends(require_admin),  # только ADMIN
):
    """Список модераторов (только ADMIN)."""
    service = ModeratorAdminService(db)
    moderators, total_count = service.list_moderators(
        limit=limit,
        offset=offset,
        is_active=is_active,
    )
    return PaginatedModerators(
        items=moderators,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


@router.post("/moderators", response_model=ModeratorResponse, status_code=status.HTTP_201_CREATED)
def create_moderator(
    request: ModeratorCreateRequest,
    db: Session = Depends(get_db),
    current_moderator_id: UUID = Depends(get_current_moderator_id),
    _: bool = Depends(require_admin),  # только ADMIN
):
    """Создать модератора (только ADMIN)."""
    service = ModeratorAdminService(db)
    
    # Проверка на дубликат email
    existing = service.get_moderator_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Moderator with email {request.email} already exists",
        )
    
    moderator = service.create_moderator(request)
    return moderator


@router.get("/moderators/me", response_model=ModeratorResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_moderator_id: UUID = Depends(get_current_moderator_id),
):
    """Профиль текущего модератора."""
    service = ModeratorAdminService(db)
    moderator = service.get_moderator(current_moderator_id)
    
    if not moderator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moderator not found",
        )
    
    return moderator


@router.get("/moderators/{moderator_id}", response_model=ModeratorResponse)
def get_moderator(
    moderator_id: UUID,
    db: Session = Depends(get_db),
    current_moderator_id: UUID = Depends(get_current_moderator_id),
    _: bool = Depends(require_admin),  # только ADMIN
):
    """Карточка модератора (только ADMIN)."""
    service = ModeratorAdminService(db)
    moderator = service.get_moderator(moderator_id)
    
    if not moderator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Moderator with ID {moderator_id} not found",
        )
    
    return moderator


@router.patch("/moderators/{moderator_id}", response_model=ModeratorResponse)
def update_moderator(
    moderator_id: UUID,
    request: ModeratorUpdateRequest,
    db: Session = Depends(get_db),
    current_moderator_id: UUID = Depends(get_current_moderator_id),
    _: bool = Depends(require_admin),  # только ADMIN
):
    """Изменить модератора (только ADMIN)."""
    service = ModeratorAdminService(db)
    
    moderator = service.get_moderator(moderator_id)
    if not moderator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Moderator with ID {moderator_id} not found",
        )
    
    updated = service.update_moderator(moderator_id, request)
    return updated


@router.delete("/moderators/{moderator_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_moderator(
    moderator_id: UUID,
    db: Session = Depends(get_db),
    current_moderator_id: UUID = Depends(get_current_moderator_id),
    _: bool = Depends(require_admin),  # только ADMIN
):
    """Деактивировать модератора (soft-delete) (только ADMIN)."""
    service = ModeratorAdminService(db)
    
    moderator = service.get_moderator(moderator_id)
    if not moderator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Moderator with ID {moderator_id} not found",
        )
    
    # Нельзя деактивировать самого себя
    if moderator_id == current_moderator_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot deactivate your own account",
        )
    
    service.deactivate_moderator(moderator_id)
    return None