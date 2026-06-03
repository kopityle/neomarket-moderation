from sqlalchemy import Column, String, Boolean, Text, Index
from app.models.base import BaseModel
import uuid


class BlockingReason(BaseModel):
    __tablename__ = "blocking_reasons"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    hard_block = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    __table_args__ = (
        Index('idx_blocking_reasons_hard_block', 'hard_block'),
        Index('idx_blocking_reasons_is_active', 'is_active'),
    )