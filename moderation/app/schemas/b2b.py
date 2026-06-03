from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Dict, Union
from uuid import UUID
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ========== Входящие данные от B2B ==========

class B2BEventType(str, Enum):
    PRODUCT_CREATED = "PRODUCT_CREATED"
    PRODUCT_EDITED = "PRODUCT_EDITED"
    PRODUCT_DELETED = "PRODUCT_DELETED"


class EventProductCreated(BaseModel):
    product_id: UUID
    seller_id: UUID
    category_id: Optional[UUID] = None
    queue_priority: int = Field(default=3, ge=1, le=4)
    json_after: Dict[str, Any]


class EventProductEdited(BaseModel):
    product_id: UUID
    seller_id: UUID
    category_id: Optional[UUID] = None
    queue_priority: int = Field(default=3, ge=1, le=4)
    json_before: Dict[str, Any]
    json_after: Dict[str, Any]


class EventProductDeleted(BaseModel):
    product_id: UUID


class IncomingB2BEvent(BaseModel):
    event_type: B2BEventType
    idempotency_key: UUID = Field(..., description="Ключ идемпотентности (TTL 24 часа)")
    occurred_at: datetime
    payload: Union[EventProductCreated, EventProductEdited, EventProductDeleted]


# ========== Исходящие данные в B2B ==========

class ModerationEventType(str, Enum):
    MODERATED = "MODERATED"
    BLOCKED = "BLOCKED"


class FieldReport(BaseModel):
    field_path: str = Field(..., description="JSONPath к проблемному полю")
    sku_id: Optional[UUID] = None
    message: str = Field(..., max_length=1000)
    severity: str = Field(default="ERROR")
    
    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in ['INFO', 'WARNING', 'ERROR']:
            raise ValueError('severity must be INFO, WARNING, or ERROR')
        return v


class ModerationEventRequest(BaseModel):
    idempotency_key: UUID = Field(..., description="Ключ идемпотентности")
    product_id: UUID = Field(..., description="ID товара")
    event_type: ModerationEventType
    moderator_id: Optional[UUID] = None
    moderator_comment: Optional[str] = Field(None, max_length=2000)
    blocking_reason_id: Optional[UUID] = Field(
        None, 
        description="Обязательно при BLOCKED (B2B принимает только одну причину)"
    )
    hard_block: bool = Field(
        default=False,
        description="true → HARD_BLOCKED, false → BLOCKED"
    )
    field_reports: Optional[List[FieldReport]] = None
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


# ========== Модели для работы с B2B API (если нужны) ==========

class B2BCategory(BaseModel):
    id: UUID
    name: str


class B2BImage(BaseModel):
    url: str
    ordering: int = 0


class B2BCharacteristic(BaseModel):
    name: str
    value: str


class B2BSKU(BaseModel):
    id: UUID
    name: str
    price: int
    discount: int = Field(0, description="Скидка в копейках")
    old_price: Optional[int] = Field(None, description="Старая цена для зачёркивания")
    active_quantity: int = Field(..., description="Доступное количество")
    characteristics: List[B2BCharacteristic] = []


class B2BProduct(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    status: str
    seller_id: UUID
    category: B2BCategory
    images: List[B2BImage] = []
    characteristics: List[B2BCharacteristic] = []
    skus: List[B2BSKU] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    total_count: int
    limit: int
    offset: int


class B2BProductListResponse(BaseModel):
    items: List[B2BProduct]
    pagination: PaginationMeta


# ========== Общие модели ==========

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = Field(default="Bearer")
    expires_in: int = Field(..., description="TTL access-токена в секундах")
    user_id: UUID
    role: Optional[str] = Field(None, description="MODERATOR или ADMIN")


# ========== Вспомогательные функции ==========

def create_moderation_event_from_decision(
    product_id: UUID,
    decision: str,  # APPROVED, BLOCKED, HARD_BLOCKED
    blocking_reason_ids: List[UUID],
    comment: Optional[str],
    field_reports: Optional[List[FieldReport]]
) -> ModerationEventRequest:
    """
    Создаёт событие для отправки в B2B.
    
    Note: B2B принимает только одну причину блокировки (blocking_reason_id),
    поэтому из списка берётся первый элемент. Остальные причины (если есть)
    логируются как предупреждение, но не теряются — они сохраняются в тикете
    модерации для аудита.
    """
    if decision == "APPROVED":
        return ModerationEventRequest(
            idempotency_key=UUID.uuid4(),
            product_id=product_id,
            event_type=ModerationEventType.MODERATED,
            moderator_comment=comment,
            field_reports=field_reports,
            occurred_at=datetime.utcnow()
        )
    
    # BLOCKED или HARD_BLOCKED
    if not blocking_reason_ids:
        raise ValueError("blocking_reason_ids required for BLOCKED/HARD_BLOCKED decision")
    
    hard_block = (decision == "HARD_BLOCKED")
    primary_reason_id = blocking_reason_ids[0]
    
    if len(blocking_reason_ids) > 1:
        logger.warning(
            f"Multiple blocking reasons ({len(blocking_reason_ids)}) provided for product {product_id}. "
            f"B2B accepts only one reason. Using primary: {primary_reason_id}. "
            f"All reasons: {blocking_reason_ids}"
        )
    
    return ModerationEventRequest(
        idempotency_key=UUID.uuid4(),
        product_id=product_id,
        event_type=ModerationEventType.BLOCKED,
        moderator_comment=comment,
        blocking_reason_id=primary_reason_id,
        hard_block=hard_block,
        field_reports=field_reports,
        occurred_at=datetime.utcnow()
    )