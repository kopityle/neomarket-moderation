from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# ========== Входящие запросы (по канону OpenAPI) ==========

class BlockDecisionRequest(BaseModel):
    """Запрос на блокировку тикета POST /api/v1/tickets/{ticket_id}/block"""
    blocking_reason_ids: List[UUID] = Field(
        ..., 
        min_length=1,
        description="Список UUID причин блокировки"
    )
    comment: Optional[str] = Field(
        None, 
        max_length=2000,
        description="Комментарий модератора"
    )
    field_reports: Optional[List["FieldReport"]] = Field(
        None,
        description="Детальные замечания по отдельным полям товара"
    )


class ApproveDecisionRequest(BaseModel):
    """Запрос на одобрение тикета POST /api/v1/tickets/{ticket_id}/approve"""
    comment: Optional[str] = Field(
        None, 
        max_length=2000,
        description="Комментарий модератора"
    )


# ========== Компоненты ответа (по канону OpenAPI) ==========

class FieldReport(BaseModel):
    """Детальный отчёт по полю товара"""
    field_path: str = Field(
        ...,
        description="JSONPath-подобный путь к проблемному полю, например images[0].url"
    )
    message: str = Field(..., max_length=1000, description="Описание проблемы")
    severity: str = Field(
        default="ERROR",
        description="Уровень критичности: INFO, WARNING, ERROR"
    )
    sku_id: Optional[UUID] = Field(None, description="ID SKU, если проблема у конкретного артикула")


class TicketHistoryEntry(BaseModel):
    """Запись в истории тикета"""
    at: datetime = Field(..., description="Время события")
    action: str = Field(
        ...,
        description="CREATED | CLAIMED | RELEASED | APPROVED | BLOCKED | HARD_BLOCKED | AUTO_RETURNED"
    )
    moderator_id: Optional[UUID] = Field(None, description="ID модератора (если применимо)")
    comment: Optional[str] = Field(None, description="Комментарий")


# Для избежания циклических импортов
from app.schemas.reason import BlockingReason  # noqa: E402