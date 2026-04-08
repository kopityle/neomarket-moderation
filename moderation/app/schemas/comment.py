from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class ModerationCommentBase(BaseModel):
    task_id: UUID  # int → UUID
    user_id: UUID
    message: str = Field(..., min_length=1, max_length=2000)
    is_from_moderator: bool


class ModerationCommentCreate(ModerationCommentBase):
    pass


class ModerationComment(ModerationCommentBase):
    id: UUID  # int → UUID
    created_at: datetime

    class Config:
        from_attributes = True