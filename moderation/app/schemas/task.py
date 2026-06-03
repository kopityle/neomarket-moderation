from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

from app.schemas.decision import FieldReport, TicketHistoryEntry
from app.schemas.reason import BlockingReason
from app.schemas.snapshot import DiffEntry

class TaskStatus(str, Enum):
    """Статусы задачи на модерацию (по канону OpenAPI)"""
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"          # вместо IN_PROGRESS
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"              # мягкая блокировка (продавец может исправить)
    HARD_BLOCKED = "HARD_BLOCKED"    # жёсткая блокировка (терминальная)


class TaskKind(str, Enum):
    """Тип тикета (по канону OpenAPI)"""
    CREATE = "CREATE"    # создание нового товара
    EDIT = "EDIT"        # редактирование существующего


class ModerationTaskBase(BaseModel):
    product_id: UUID = Field(..., description="ID товара из B2B")
    seller_id: UUID = Field(..., description="ID продавца из B2B")
    kind: TaskKind = Field(..., description="CREATE — новый товар, EDIT — редактирование")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Статус задачи")
    queue_priority: int = Field(
        default=3, 
        ge=1, 
        le=4, 
        description="Приоритет очереди: 1 — самый высокий, 4 — самый низкий"
    )
    category_id: Optional[UUID] = Field(
        None, 
        description="ID категории товара (из B2B)"
    )
    assigned_moderator_id: Optional[UUID] = Field(
        None, 
        description="ID модератора, взявшего тикет в работу (из Auth)"
    )


class ModerationTaskCreate(BaseModel):
    """Создание нового тикета (при входящем событии от B2B)"""
    product_id: UUID = Field(..., description="ID товара из B2B")
    seller_id: UUID = Field(..., description="ID продавца из B2B")
    kind: TaskKind = Field(..., description="CREATE или EDIT")
    queue_priority: int = Field(
        default=3, 
        ge=1, 
        le=4, 
        description="Приоритет очереди"
    )
    category_id: Optional[UUID] = Field(None, description="ID категории")
    json_before: Optional[dict] = Field(
        None, 
        description="Снапшот ДО изменений (только для EDIT)"
    )
    json_after: dict = Field(
        ..., 
        description="Снапшот товара на момент создания тикета"
    )


class ModerationTaskUpdate(BaseModel):
    """Обновление тикета (для внутренних нужд)"""
    status: Optional[TaskStatus] = None
    queue_priority: Optional[int] = Field(None, ge=1, le=4)
    assigned_moderator_id: Optional[UUID] = None
    category_id: Optional[UUID] = None


class ModerationTask(ModerationTaskBase):
    """Полная модель тикета (ответ API)"""
    id: UUID = Field(..., description="UUID тикета")
    
    # Поля для работы с очередью (TTL 30 минут)
    claimed_at: Optional[datetime] = Field(
        None, 
        description="Когда тикет был взят в работу"
    )
    claim_expires_at: Optional[datetime] = Field(
        None, 
        description="Когда автоматически вернётся в PENDING (claimed_at + 30 минут)"
    )
    
    # Поле решения
    decision_at: Optional[datetime] = Field(
        None, 
        description="Когда было принято решение (APPROVED/BLOCKED/HARD_BLOCKED)"
    )
    decision_comment: Optional[str] = Field(  # ← ДОБАВИТЬ ЭТО ПОЛЕ!
        None, 
        max_length=2000,
        description="Комментарий модератора к решению"
    )
    
    # Системные поля
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата последнего обновления")

    class Config:
        from_attributes = True


class ClaimTicketRequest(BaseModel):
    """Запрос на взятие тикета из очереди (/api/v1/queue/claim)"""
    queue_priority: Optional[int] = Field(None, ge=1, le=4, description="Фильтр по приоритету")
    category_ids: Optional[list[UUID]] = Field(None, description="Фильтр по категориям")


class BlockDecisionRequest(BaseModel):
    """Запрос на блокировку тикета (/api/v1/tickets/{ticket_id}/block)"""
    blocking_reason_ids: list[UUID] = Field(..., min_length=1, description="Список причин блокировки")
    comment: Optional[str] = Field(None, max_length=2000, description="Комментарий модератора")
    field_reports: Optional[list["FieldReport"]] = Field(None, description="Детальные замечания по полям")


class ApproveDecisionRequest(BaseModel):
    """Запрос на одобрение тикета (/api/v1/tickets/{ticket_id}/approve)"""
    comment: Optional[str] = Field(None, max_length=2000, description="Комментарий модератора")

class PaginatedTickets(BaseModel):
    items: List[ModerationTask]
    total_count: int
    limit: int
    offset: int

# Для избежания циклических импортов
class TicketResponse(ModerationTask):
    """
    Ответ API для тикета (алиас для ModerationTask).
    По канону OpenAPI: TicketResponse
    """
    pass


class TicketDetailResponse(TicketResponse):
    """
    Детальный ответ API для тикета с снапшотами и историей.
    По канону OpenAPI: TicketDetailResponse
    """
    json_before: Optional[dict] = Field(None, description="Снапшот ДО изменений (только для EDIT)")
    json_after: dict = Field(..., description="Снапшот товара на момент создания тикета")
    diff: Optional[List["DiffEntry"]] = Field(None, description="Вычисленный diff для UI")
    field_reports: Optional[List["FieldReport"]] = Field(None, description="Детальные замечания по полям")
    blocking_reasons: Optional[List["BlockingReason"]] = Field(None, description="Причины блокировки")
    decision_comment: Optional[str] = Field(None, description="Комментарий модератора к решению")
    history: Optional[List["TicketHistoryEntry"]] = Field(None, description="История изменений тикета")

