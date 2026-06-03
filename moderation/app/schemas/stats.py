# app/schemas/stats.py
from pydantic import BaseModel
from typing import Optional, Dict
from uuid import UUID


class StatsOverview(BaseModel):
    """Сводка по очереди и решениям (по канону OpenAPI)"""
    pending_count: int
    in_review_count: int
    approved_count: int
    blocked_count: int
    hard_blocked_count: int
    avg_review_time_seconds: Optional[int] = None
    pending_by_priority: Optional[Dict[str, int]] = None  # ← типизированный dict


class ModeratorStats(BaseModel):
    """Производительность модератора (по канону OpenAPI)"""
    moderator_id: UUID
    moderator_name: str
    decisions_count: int
    approved_count: int
    blocked_count: int
    hard_blocked_count: int
    avg_review_time_seconds: Optional[int] = None
    released_count: int = 0  # ← добавлен default=0