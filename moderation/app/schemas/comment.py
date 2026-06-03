from pydantic import BaseModel, Field
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


class ModerationCommentCreate(ModerationCommentBase):
    """Создание комментария"""
    pass


class ModerationCommentUpdate(BaseModel):
    """Обновление комментария (только для модераторов/админов?)"""
    message: Optional[str] = Field(None, min_length=1, max_length=2000)
    is_from_moderator: Optional[bool] = None


class ModerationComment(ModerationCommentBase):
    """Полная модель комментария"""
    id: UUID = Field(..., description="UUID комментария")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата последнего обновления")

    class Config:
        from_attributes = True


class PaginatedComments(BaseModel):
    """Пагинированный список комментариев (если добавите эндпоинт)"""
    items: List[ModerationComment]  # ← List вместо list
    total_count: int
    limit: int = 20
    offset: int = 0