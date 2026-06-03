from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


# ========== Enums ==========

class TicketHistoryAction(str, Enum):
    """Действия в истории тикета (по канону OpenAPI)"""
    CREATED = "CREATED"
    CLAIMED = "CLAIMED"
    RELEASED = "RELEASED"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    HARD_BLOCKED = "HARD_BLOCKED"
    AUTO_RETURNED = "AUTO_RETURNED"


class SeverityLevel(str, Enum):
    """Уровень критичности FieldReport"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ========== Входящие запросы (по канону OpenAPI) ==========
class FieldReport(BaseModel):
    """Детальный отчёт по полю товара"""
    field_path: str = Field(
        ...,
        description="JSONPath-подобный путь к проблемному полю, например images[0].url"
    )
    message: str = Field(..., max_length=1000, description="Описание проблемы")
    severity: SeverityLevel = Field(
        default=SeverityLevel.ERROR,
        description="Уровень критичности: INFO, WARNING, ERROR"
    )
    sku_id: Optional[UUID] = Field(None, description="ID SKU, если проблема у конкретного артикула")
    
    @field_validator('field_path')
    @classmethod
    def validate_field_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('field_path cannot be empty')
        return v.strip()
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('message cannot be empty')
        return v.strip()



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





class TicketHistoryEntry(BaseModel):
    """Запись в истории тикета"""
    at: datetime = Field(..., description="Время события")
    action: TicketHistoryAction = Field(..., description="Тип события")
    moderator_id: Optional[UUID] = Field(None, description="ID модератора (если применимо)")
    comment: Optional[str] = Field(None, max_length=2000, description="Комментарий")

