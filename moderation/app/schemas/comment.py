from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ModerationCommentBase(BaseModel):
    """Базовый класс комментария"""
    task_id: UUID = Field(..., description="ID тикета")
    user_id: UUID = Field(..., description="ID пользователя (модератор или продавец)")
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="Текст комментария"
    )
    is_from_moderator: bool = Field(
        ..., 
        description="true — от модератора, false — от продавца"
    )
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError('Message cannot be empty or only whitespace')
        return stripped


class ModerationCommentCreate(ModerationCommentBase):
    """Создание комментария"""
    pass


class ModerationCommentUpdate(BaseModel):
    """Обновление комментария (только для модераторов/админов)"""
    message: Optional[str] = Field(None, min_length=1, max_length=2000)
    # is_from_moderator - НЕ ИЗМЕНЯЕТСЯ после создания
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError('Message cannot be empty or only whitespace')
            return stripped
        return v


class ModerationComment(ModerationCommentBase):
    """Полная модель комментария"""
    id: UUID = Field(..., description="UUID комментария")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата последнего обновления")
    is_edited: bool = Field(default=False, description="Был ли комментарий изменён")

    class Config:
        from_attributes = True


class PaginatedComments(BaseModel):
    """Пагинированный список комментариев"""
    items: List[ModerationComment]
    total_count: int
    limit: int = 20
    offset: int = 0


class CommentQueryParams(BaseModel):
    """Query-параметры для GET /api/v1/comments"""
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    task_id: Optional[UUID] = Field(None, description="Фильтр по ID тикета")
    user_id: Optional[UUID] = Field(None, description="Фильтр по ID пользователя")
    is_from_moderator: Optional[bool] = Field(None, description="Фильтр по типу автора")
    created_from: Optional[datetime] = Field(None, description="Начало периода")
    created_to: Optional[datetime] = Field(None, description="Конец периода")


class CommentCreateResponse(ModerationComment):
    """Ответ при создании комментария"""
    pass