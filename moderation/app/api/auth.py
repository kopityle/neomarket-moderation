# app/api/auth.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.config import settings
from app.core.exceptions import AppException

router = APIRouter(tags=["Auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """Вход модератора."""
    service = AuthService(db)
    
    moderator = service.authenticate(request.email, request.password)
    if not moderator:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Invalid email or password",
        )
    
    # Генерируем токены
    access_token = service.create_access_token(moderator.id)
    refresh_token = service.create_refresh_token(moderator.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        user_id=moderator.id,
        role=moderator.role,
    )


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(
    request: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Обновление access-токена."""
    service = AuthService(db)
    
    moderator_id = service.validate_refresh_token(request.refresh_token)
    if not moderator_id:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Invalid or expired refresh token",
        )
    
    # Отзываем старый refresh token и создаём новую пару
    service.revoke_refresh_token(request.refresh_token)
    
    access_token = service.create_access_token(moderator_id)
    refresh_token = service.create_refresh_token(moderator_id)
    
    moderator = service.get_moderator(moderator_id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        user_id=moderator_id,
        role=moderator.role if moderator else "MODERATOR",
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Выход (отзыв refresh-токена)."""
    service = AuthService(db)
    service.revoke_refresh_token(request.refresh_token)
    return None