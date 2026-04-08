from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class ProductSnapshotBase(BaseModel):
    task_id: UUID = Field(..., description="ID задачи")  # int → UUID
    product_data: Dict[str, Any] = Field(..., description="Полная копия товара + SKU из B2B")
    version: int = Field(default=1, ge=1)
    is_initial: bool = Field(default=True)


class ProductSnapshotCreate(ProductSnapshotBase):
    pass


class ProductSnapshot(ProductSnapshotBase):
    id: UUID  # int → UUID
    created_at: datetime

    class Config:
        from_attributes = True