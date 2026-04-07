from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ProductSnapshotBase(BaseModel):
    task_id: int
    product_data: Dict[str, Any] = Field(..., description="Полная копия товара + SKU из B2B")
    version: int = Field(default=1, ge=1)
    is_initial: bool = Field(default=True, description="true=первая версия, false=после изменений")


class ProductSnapshotCreate(ProductSnapshotBase):
    pass


class ProductSnapshot(ProductSnapshotBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True