from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List
from uuid import UUID
from enum import Enum


class StatsPeriod(str, Enum):
    """Период для статистики (по канону OpenAPI)"""
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"


class StatsOverview(BaseModel):
    """Сводка по очереди и решениям (по канону OpenAPI)"""
    pending_count: int = Field(..., description="Количество тикетов в очереди", example=25)
    in_review_count: int = Field(..., description="Количество тикетов в работе", example=3)
    approved_count: int = Field(..., description="Одобрено за период", example=120)
    blocked_count: int = Field(..., description="Заблокировано (soft) за период", example=15)
    hard_blocked_count: int = Field(..., description="Заблокировано (hard) за период", example=2)
    avg_review_time_seconds: Optional[int] = Field(
        None,
        description="Среднее время рассмотрения (секунды)",
        example=180
    )
    pending_by_priority: Optional[Dict[str, int]] = Field(
        None,
        description="Количество PENDING тикетов по приоритетам (1-4)",
        example={"1": 5, "2": 3, "3": 10, "4": 7}
    )

    @field_validator('pending_by_priority')
    @classmethod
    def validate_priorities(cls, v: Optional[Dict[str, int]]) -> Optional[Dict[str, int]]:
        if v is not None:
            for key in v.keys():
                if key not in ['1', '2', '3', '4']:
                    raise ValueError(f'Invalid priority key: {key}, must be 1,2,3,4')
        return v


class ModeratorStats(BaseModel):
    """Производительность модератора (по канону OpenAPI)"""
    moderator_id: UUID = Field(..., description="ID модератора")
    moderator_name: str = Field(..., description="Имя модератора", example="Иван Иванов")
    decisions_count: int = Field(..., description="Всего решений", example=150)
    approved_count: int = Field(..., description="Одобрено", example=120)
    blocked_count: int = Field(..., description="Заблокировано (soft)", example=28)
    hard_blocked_count: int = Field(..., description="Заблокировано (hard)", example=2)
    avg_review_time_seconds: Optional[int] = Field(
        None,
        description="Среднее время рассмотрения (секунды)",
        example=210
    )
    released_count: int = Field(
        0,
        description="Сколько раз тикеты возвращались в очередь без решения",
        example=5
    )


class StatsQueryParams(BaseModel):
    """Query-параметры для эндпоинтов статистики"""
    period: StatsPeriod = Field(
        default=StatsPeriod.TODAY,
        description="Период: today, week, month"
    )


class StatsTimeSeries(BaseModel):
    """Временной ряд статистики (для графиков)"""
    date: str = Field(..., description="Дата (YYYY-MM-DD)", example="2026-06-01")
    approved_count: int = Field(0, description="Количество одобрений")
    blocked_count: int = Field(0, description="Количество блокировок")
    avg_review_time: Optional[int] = Field(
        None,
        description="Среднее время рассмотрения (секунды)"
    )


# Для обратной совместимости (если API возвращает строки)
StatsOverview.model_rebuild()