from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime


class B2BCategory(BaseModel):
    id: int  # в B2B категории могут быть INTEGER
    name: str


class B2BImage(BaseModel):
    url: str
    ordering: int = 0


class B2BCharacteristic(BaseModel):
    name: str
    value: str


class B2BSKU(BaseModel):
    id: int  # SKU id в B2B может быть INTEGER
    name: str
    price: int
    activeQuantity: int
    characteristics: List[B2BCharacteristic] = []


class B2BProduct(BaseModel):
    """Товар из B2B сервиса"""
    id: UUID  # ← int → UUID
    title: str
    description: Optional[str] = None
    status: str
    seller_id: UUID  # ← добавить seller_id
    category: B2BCategory
    images: List[B2BImage] = []
    characteristics: List[B2BCharacteristic] = []
    skus: List[B2BSKU] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None


class B2BProductListResponse(BaseModel):
    items: List[B2BProduct]
    pagination: dict


class ModerationCallbackRequest(BaseModel):
    """Запрос в B2B после модерации"""
    product_id: int
    decision: str  # APPROVED, DECLINED
    blocking_reason_id: Optional[int] = None
    comment: Optional[str] = None