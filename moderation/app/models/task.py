from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel


class ModerationTask(BaseModel):
    __tablename__ = "moderation_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, nullable=False)  # ID из B2B
    seller_id = Column(String(36), nullable=False)  # UUID продавца из B2B
    
    priority = Column(Integer, default=0)  # 0 = обычный, 1 = высокий
    status = Column(String(20), default="PENDING")
    # PENDING, IN_PROGRESS, APPROVED, DECLINED
    
    assigned_to = Column(String(36), nullable=True)  # модератор (user_id из Auth)
    
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    snapshots = relationship("ProductSnapshot", back_populates="task", cascade="all, delete-orphan")
    decisions = relationship("ModerationDecision", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("ModerationComment", back_populates="task", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_tasks_status', 'status'),
        Index('idx_tasks_priority', 'priority'),
        Index('idx_tasks_created', 'created_at'),
    )