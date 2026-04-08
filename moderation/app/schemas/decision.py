from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


class DecisionType(str, Enum):
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


class ModerationDecisionBase(BaseModel):
    task_id: UUID  # int → UUID
    moderator_id: UUID
    decision: DecisionType
    blocking_reason_id: Optional[int] = None
    comment: Optional[str] = Field(None, max_length=1000)


class ModerationDecisionCreate(ModerationDecisionBase):
    pass


class ModerationDecision(ModerationDecisionBase):
    id: UUID  # int → UUID
    created_at: datetime

    class Config:
        from_attributes = True