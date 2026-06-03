# app/schemas/auth.py
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional


class LoginRequest(BaseModel):
    """Запрос на вход модератора"""
    email: str = Field(..., description="Email модератора")
    password: str = Field(..., description="Пароль")


class RefreshRequest(BaseModel):
    """Запрос на обновление токена"""
    refresh_token: str = Field(..., description="Refresh token")


class TokenResponse(BaseModel):
    """Ответ с токенами"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(..., description="TTL access-токена в секундах")
    user_id: UUID
    role: Optional[str] = Field(None, description="MODERATOR или ADMIN")