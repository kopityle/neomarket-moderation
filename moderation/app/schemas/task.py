from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

from app.schemas.decision import (
    FieldReport, 
    TicketHistoryEntry,
    BlockDecisionRequest,
    ApproveDecisionRequest
)
from app.schemas.reason import BlockingReason
from app.schemas.snapshot import DiffEntry


class TaskStatus(str, Enum):
    """Статусы задачи на модерацию (по канону OpenAPI)"""
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    HARD_BLOCKED = "HARD_BLOCKED"


class TaskKind(str, Enum):
    """Тип тикета (по канону OpenAPI)"""
    CREATE = "CREATE"
    EDIT = "EDIT"


class ModerationTaskBase(BaseModel):
    """Базовая модель тикета"""
    product_id: UUID = Field(..., description="ID товара из B2B")
    seller_id: UUID = Field(..., description="ID продавца из B2B")
    kind: TaskKind = Field(..., description="CREATE или EDIT")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    queue_priority: int = Field(
        default=3, 
        ge=1, 
        le=4, 
        description="Приоритет: 1 — высокий, 4 — низкий"
    )
    category_id: Optional[UUID] = Field(None, description="ID категории")
    assigned_moderator_id: Optional[UUID] = Field(None, description="ID модератора")


class ModerationTaskCreate(BaseModel):
    """Создание нового тикета (при входящем событии от B2B)"""
    product_id: UUID
    seller_id: UUID
    kind: TaskKind
    queue_priority: int = Field(3, ge=1, le=4)
    category_id: Optional[UUID] = None
    json_before: Optional[dict] = Field(None, description="Только для EDIT")
    json_after: dict = Field(..., description="Снапшот на момент создания")

    @field_validator('queue_priority')
    @classmethod
    def validate_priority(cls, v: int) -> int:
        if v < 1 or v > 4:
            raise ValueError('queue_priority must be 1-4')
        return v


class ModerationTaskUpdate(BaseModel):
    """Обновление тикета (для внутренних нужд)"""
    status: Optional[TaskStatus] = None
    queue_priority: Optional[int] = Field(None, ge=1, le=4)
    assigned_moderator_id: Optional[UUID] = None
    category_id: Optional[UUID] = None


class ModerationTask(ModerationTaskBase):
    """Полная модель тикета (ответ API)"""
    id: UUID = Field(..., description="UUID тикета")
    claimed_at: Optional[datetime] = Field(None, description="Когда взят в работу")
    claim_expires_at: Optional[datetime] = Field(
        None, 
        description="Автоматический возврат в PENDING (claimed_at + 30 минут)"
    )
    decision_at: Optional[datetime] = Field(None, description="Когда принято решение")
    decision_comment: Optional[str] = Field(None, max_length=2000)
    created_at: datetime
    updated_at: Optional[datetime] = None

    def is_claim_expired(self) -> bool:
        """Проверяет, истекло ли время захвата тикета"""
        if self.status != TaskStatus.IN_REVIEW or not self.claim_expires_at:
            return False
        return datetime.utcnow() > self.claim_expires_at

    def can_be_claimed(self) -> bool:
        """Может ли тикет быть взят в работу"""
        return self.status == TaskStatus.PENDING and self.assigned_moderator_id is None

    class Config:
        from_attributes = True


# ========== Request/Response Models ==========

class ClaimTicketRequest(BaseModel):
    """Запрос на взятие тикета из очереди"""
    queue_priority: Optional[int] = Field(None, ge=1, le=4)
    category_ids: Optional[List[UUID]] = Field(None, description="Фильтр по категориям")




class TicketResponse(ModerationTask):
    """Ответ API для тикета (базовый)"""
    pass


class TicketDetailResponse(TicketResponse):
    """Детальный ответ API с снапшотами и историей"""
    json_before: Optional[dict] = Field(None, description="Снапшот ДО изменений")
    json_after: dict = Field(..., description="Снапшот товара на момент создания")
    diff: Optional[List[DiffEntry]] = Field(None, description="Вычисленный diff для UI")
    field_reports: Optional[List[FieldReport]] = None
    blocking_reasons: Optional[List[BlockingReason]] = None
    history: Optional[List[TicketHistoryEntry]] = None


class PaginatedTickets(BaseModel):
    """Пагинированный список тикетов"""
    items: List[TicketResponse]
    total_count: int
    limit: int
    offset: int


# ========== Query Parameters ==========

class QueueQueryParams(BaseModel):
    """Query-параметры для GET /api/v1/queue"""
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    queue_priority: Optional[int] = Field(None, ge=1, le=4)
    category_id: Optional[UUID] = None
    seller_id: Optional[UUID] = None


class TicketsQueryParams(BaseModel):
    """Query-параметры для GET /api/v1/tickets"""
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    status: Optional[TaskStatus] = None
    moderator_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    seller_id: Optional[UUID] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None



    # ========== Model rebuilds for resolving forward references ==========

TicketDetailResponse.model_rebuild()
ModerationTask.model_rebuild()
PaginatedTickets.model_rebuild()
QueueQueryParams.model_rebuild()
TicketsQueryParams.model_rebuild()