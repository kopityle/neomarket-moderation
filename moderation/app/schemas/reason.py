from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID
from enum import Enum
import re


class BlockingReasonBase(BaseModel):
    """Базовая схема причины блокировки (по канону OpenAPI)"""
    code: str = Field(
        ..., 
        max_length=64, 
        pattern=r'^[A-Z_]+$',
        description="Код причины, только заглавные буквы и подчёркивания, например FORBIDDEN_GOODS"
    )
    title: str = Field(..., max_length=200, description="Название причины")
    description: Optional[str] = Field(None, max_length=2000, description="Описание")
    hard_block: bool = Field(
        ...,
        description="true → HARD_BLOCKED (терминально), false → BLOCKED (можно исправить)"
    )
    is_active: bool = Field(default=True, description="Активна ли причина")

    @field_validator('code')
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        if not re.match(r'^[A-Z_]+$', v):
            raise ValueError('Code must contain only uppercase letters and underscores')
        return v


class BlockingReasonCreate(BlockingReasonBase):
    """Создание причины блокировки (admin)"""
    pass


class BlockingReasonUpdate(BaseModel):
    """Обновление причины блокировки (admin)"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None
    # hard_block НЕЛЬЗЯ менять после создания (по канону)


class BlockingReason(BlockingReasonBase):
    """Полная модель причины блокировки"""
    id: UUID = Field(..., description="UUID причины блокировки")

    class Config:
        from_attributes = True


# app/schemas/reason.py (добавить в конец)

class BlockingReasonResponse(BlockingReasonBase):
    """Ответ API для причины блокировки (по канону OpenAPI)"""
    id: UUID = Field(..., description="UUID причины блокировки")
    code: str
    title: str
    description: Optional[str] = None
    hard_block: bool
    is_active: bool

    class Config:
        from_attributes = True

# ========== Для обратной совместимости (если нужно) ==========
# Если у вас уже есть данные с Integer ID, можно добавить алиас:
# id: Union[int, UUID] = Field(..., description="ID причины блокировки")
# Но лучше мигрировать на UUID.