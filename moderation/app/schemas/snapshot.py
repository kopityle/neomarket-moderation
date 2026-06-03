from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from uuid import UUID
from enum import Enum


class SnapshotType(str, Enum):
    """Тип снапшота (по канону OpenAPI)"""
    BEFORE = "BEFORE"   # json_before — только для EDIT
    AFTER = "AFTER"     # json_after — всегда


class ProductSnapshotBase(BaseModel):
    """Базовый класс снапшота (внутреннее хранение)"""
    task_id: UUID = Field(..., description="ID тикета")
    snapshot_type: SnapshotType = Field(..., description="BEFORE или AFTER")
    data: Dict[str, Any] = Field(..., description="Снапшот товара")


class ProductSnapshotCreate(BaseModel):
    """Создание снапшота (внутреннее использование)"""
    task_id: UUID
    snapshot_type: SnapshotType
    data: Dict[str, Any]


class ProductSnapshot(ProductSnapshotBase):
    """Полная модель снапшота (внутреннее хранение)"""
    id: UUID = Field(..., description="UUID снапшота")

    class Config:
        from_attributes = True


# ========== API-схемы для ответов (по канону OpenAPI) ==========

class TicketSnapshotsResponse(BaseModel):
    """
    Снапшоты в ответе API (TicketDetailResponse)
    По канону: ровно 2 снапшота на тикет
    """
    json_before: Optional[Dict[str, Any]] = Field(
        None,
        description="Снапшот товара ДО изменений (только для kind=EDIT, иначе null)"
    )
    json_after: Dict[str, Any] = Field(
        ...,
        description="Снапшот товара на момент создания тикета"
    )


class DiffEntry(BaseModel):
    """Опциональный diff для UI (по канону OpenAPI)"""
    field: str = Field(..., description="Имя поля")
    old_value: Optional[Any] = Field(None, description="Старое значение")
    new_value: Optional[Any] = Field(None, description="Новое значение")


class TicketDetailResponse(TicketSnapshotsResponse):
    """
    Полный ответ /api/v1/tickets/{ticket_id}
    (снапшоты + diff + остальные поля)
    """
    diff: Optional[list[DiffEntry]] = Field(
        None,
        description="Вычисленный diff для UI (опционально)"
    )
    # Остальные поля TicketResponse будут добавлены через наследование
    # или композицию в основном файле task.py