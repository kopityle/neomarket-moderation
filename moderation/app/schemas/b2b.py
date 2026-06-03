from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


# ========== Входящие данные от B2B (как в OpenAPI Moderation) ==========

class B2BEventType(str, Enum):
    """Типы событий от B2B (по канону)"""
    PRODUCT_CREATED = "PRODUCT_CREATED"
    PRODUCT_EDITED = "PRODUCT_EDITED"
    PRODUCT_DELETED = "PRODUCT_DELETED"


class EventProductCreated(BaseModel):
    """Событие создания товара"""
    product_id: UUID
    seller_id: UUID
    category_id: Optional[UUID] = None
    queue_priority: int = Field(default=3, ge=1, le=4)
    json_after: dict


class EventProductEdited(BaseModel):
    """Событие редактирования товара"""
    product_id: UUID
    seller_id: UUID
    category_id: Optional[UUID] = None
    queue_priority: int = Field(default=3, ge=1, le=4)
    json_before: dict
    json_after: dict


class EventProductDeleted(BaseModel):
    """Событие удаления товара"""
    product_id: UUID


class IncomingB2BEvent(BaseModel):
    """Входящее событие от B2B (по канону OpenAPI Moderation)"""
    event_type: B2BEventType
    idempotency_key: UUID = Field(..., description="Ключ идемпотентности (TTL 24 часа)")
    occurred_at: datetime
    payload: dict  # oneOf: EventProductCreated/Edited/Deleted


# ========== Исходящие данные в B2B (по канону B2B OpenAPI) ==========

class ModerationEventType(str, Enum):
    """Типы событий от Moderation в B2B"""
    MODERATED = "MODERATED"
    BLOCKED = "BLOCKED"


class ModerationEventRequest(BaseModel):
    """
    Запрос от Moderation в B2B на /api/v1/moderation/events
    (по канону neomarket-b2b.yaml)
    """
    idempotency_key: UUID = Field(..., description="Ключ идемпотентности")
    product_id: UUID = Field(..., description="ID товара")
    event_type: ModerationEventType = Field(..., description="MODERATED или BLOCKED")
    moderator_id: Optional[UUID] = None
    moderator_comment: Optional[str] = Field(None, max_length=2000)
    blocking_reason_id: Optional[UUID] = Field(
        None, 
        description="Обязательно при BLOCKED"
    )
    hard_block: bool = Field(
        default=False,
        description="true → HARD_BLOCKED, false → BLOCKED"
    )
    field_reports: Optional[List["FieldReport"]] = None
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class FieldReport(BaseModel):
    """Детальный отчёт по полю (единый формат для Moderation и B2B)"""
    field_path: str = Field(..., description="JSONPath к проблемному полю")
    sku_id: Optional[UUID] = None
    message: str = Field(..., max_length=1000)
    severity: str = Field(default="ERROR", description="INFO, WARNING, ERROR")


# ========== Модели для получения данных из B2B (для формирования снапшотов) ==========

class B2BCategory(BaseModel):
    """Категория из B2B (UUID!)"""
    id: UUID  # ← ИСПРАВЛЕНО: было int, теперь UUID
    name: str


class B2BImage(BaseModel):
    url: str
    ordering: int = 0


class B2BCharacteristic(BaseModel):
    name: str
    value: str


class B2BSKU(BaseModel):
    """SKU из B2B (UUID!)"""
    id: UUID  # ← ИСПРАВЛЕНО: было int, теперь UUID
    name: str
    price: int
    active_quantity: int = Field(..., alias="activeQuantity")  # alias для camelCase
    characteristics: List[B2BCharacteristic] = []

    class Config:
        populate_by_name = True  # позволяет использовать оба имени


class B2BProduct(BaseModel):
    """Товар из B2B сервиса"""
    id: UUID
    title: str
    description: Optional[str] = None
    status: str
    seller_id: UUID
    category: B2BCategory      # ← теперь UUID
    images: List[B2BImage] = []
    characteristics: List[B2BCharacteristic] = []
    skus: List[B2BSKU] = []    # ← теперь UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None


class B2BProductListResponse(BaseModel):
    items: List[B2BProduct]
    pagination: dict


# ========== Вспомогательные функции ==========

def create_moderation_event_from_decision(
    product_id: UUID,
    decision: str,  # APPROVED, BLOCKED, HARD_BLOCKED
    blocking_reason_ids: List[UUID],
    comment: Optional[str],
    field_reports: Optional[List[FieldReport]]
) -> ModerationEventRequest:
    """
    Создаёт событие для отправки в B2B на основе решения модератора.
    """
    if decision == "APPROVED":
        return ModerationEventRequest(
            idempotency_key=UUID.uuid4(),
            product_id=product_id,
            event_type=ModerationEventType.MODERATED,
            moderator_comment=comment,
            occurred_at=datetime.utcnow()
        )
    else:
        # BLOCKED или HARD_BLOCKED
        hard_block = (decision == "HARD_BLOCKED")
        # Берём первый blocking_reason_id (B2B пока поддерживает один)
        blocking_reason_id = blocking_reason_ids[0] if blocking_reason_ids else None
        
        return ModerationEventRequest(
            idempotency_key=UUID.uuid4(),
            product_id=product_id,
            event_type=ModerationEventType.BLOCKED,
            moderator_comment=comment,
            blocking_reason_id=blocking_reason_id,
            hard_block=hard_block,
            field_reports=field_reports,
            occurred_at=datetime.utcnow()
        )