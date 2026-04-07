from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BlockingReasonBase(BaseModel):
    code: str = Field(..., max_length=50, description="Код причины (уникальный)")
    name: str = Field(..., max_length=255, description="Название причины")
    description: Optional[str] = Field(None, description="Описание")
    is_active: bool = Field(default=True)


class BlockingReasonCreate(BlockingReasonBase):
    pass


class BlockingReason(BlockingReasonBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True