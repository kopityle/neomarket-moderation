# app/models/reason.py
from sqlalchemy import Column, String, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel
import uuid


class BlockingReason(BaseModel):
    __tablename__ = "blocking_reasons"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # ← UUID
    code = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    hard_block = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    __table_args__ = (
        Index('idx_blocking_reasons_hard_block', 'hard_block'),
        Index('idx_blocking_reasons_is_active', 'is_active'),
    )