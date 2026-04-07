from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class ModerationCommentBase(BaseModel):
    task_id: int
    user_id: UUID = Field(..., description="Кто написал (модератор или продавец)")
    message: str = Field(..., min_length=1, max_length=2000)
    is_from_moderator: bool = Field(..., description="true=от модератора, false=от продавца")


class ModerationCommentCreate(ModerationCommentBase):
    pass


class ModerationComment(ModerationCommentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True