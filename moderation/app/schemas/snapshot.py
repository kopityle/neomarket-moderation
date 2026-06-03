from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any, Dict, List
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

    @field_validator('data')
    @classmethod
    def validate_data_not_empty(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not v:
            raise ValueError('Snapshot data cannot be empty')
        return v


class ProductSnapshotCreate(ProductSnapshotBase):
    """Создание снапшота (внутреннее использование)"""
    pass


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
        description="Снапшот товара ДО изменений (только для kind=EDIT, иначе null)",
        example={"title": "Старое название"}
    )
    json_after: Dict[str, Any] = Field(
        ...,
        description="Снапшот товара на момент создания тикета",
        example={"title": "Новое название", "price": 10000}
    )


class DiffEntry(BaseModel):
    """Опциональный diff для UI (по канону OpenAPI)"""
    field: str = Field(..., description="Имя поля", example="price")
    old_value: Optional[Any] = Field(None, description="Старое значение", example=10000)
    new_value: Optional[Any] = Field(None, description="Новое значение", example=15000)

    @classmethod
    def from_dict(cls, old: Dict[str, Any], new: Dict[str, Any]) -> List["DiffEntry"]:
        """
        Вычисляет diff между двумя словарями.
        Используется для UI модератора.
        """
        diff = []
        all_keys = set(old.keys()) | set(new.keys())
        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                diff.append(cls(field=key, old_value=old_val, new_value=new_val))
        return diff


# NOTE: TicketDetailResponse определён в task.py, так как требует
# наследования от TicketResponse и содержит дополнительные поля.