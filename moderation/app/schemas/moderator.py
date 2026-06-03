# app/schemas/moderator.py
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class ModeratorRole(str, Enum):
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


class ModeratorBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: ModeratorRole = ModeratorRole.MODERATOR
    is_active: bool = True
    category_specializations: List[UUID] = []


class ModeratorCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12)
    first_name: str = Field(..., max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: ModeratorRole = ModeratorRole.MODERATOR
    category_specializations: List[UUID] = []


class ModeratorUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: Optional[ModeratorRole] = None
    is_active: Optional[bool] = None
    category_specializations: Optional[List[UUID]] = None


class ModeratorResponse(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: Optional[str] = None
    role: ModeratorRole
    is_active: bool
    category_specializations: List[UUID] = []
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedModerators(BaseModel):
    items: List[ModeratorResponse]
    total_count: int
    limit: int
    offset: int