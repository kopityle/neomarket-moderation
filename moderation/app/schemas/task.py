from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class TaskStatus(str, Enum):
    """Статусы задачи на модерацию"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


class ModerationTaskBase(BaseModel):
    product_id: int = Field(..., gt=0, description="ID товара из B2B")
    seller_id: UUID = Field(..., description="ID продавца из B2B")
    priority: int = Field(default=0, ge=0, le=1, description="0=обычный, 1=высокий")
    assigned_to: Optional[UUID] = Field(None, description="ID модератора из Auth")


class ModerationTaskCreate(ModerationTaskBase):
    pass


class ModerationTaskUpdate(BaseModel):
    priority: Optional[int] = Field(None, ge=0, le=1)
    status: Optional[TaskStatus] = None
    assigned_to: Optional[UUID] = None


class ModerationTask(ModerationTaskBase):
    id: int
    status: TaskStatus = TaskStatus.PENDING
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True