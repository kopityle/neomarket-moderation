from sqlalchemy import Column, String, DateTime, Index, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid
from sqlalchemy.dialects.postgresql import UUID

class ModerationTask(BaseModel):
    __tablename__ = "moderation_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(String(36), nullable=False, index=True)
    seller_id = Column(String(36), nullable=False)
    category_id = Column(String(36), nullable=True)
    
    # Тип тикета: CREATE или EDIT
    kind = Column(String(20), nullable=False)  # CREATE, EDIT
    
    # Статус: PENDING, IN_REVIEW, APPROVED, BLOCKED, HARD_BLOCKED
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    
    # Приоритет очереди: 1-4
    queue_priority = Column(Integer, nullable=False, default=3, index=True)
    
    # Кто взял тикет в работу
    assigned_moderator_id = Column(String(36), nullable=True, index=True)
    
    # Снапшоты
    json_before = Column(JSON, nullable=True)
    json_after = Column(JSON, nullable=False)
    
    # Временные метки для очереди
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    claim_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Решение
    decision_at = Column(DateTime(timezone=True), nullable=True)
    decision_comment = Column(String(2000), nullable=True)
    blocking_reason_id = Column(String(36), nullable=True)  # UUID причины блокировки
    
    # Связи
    snapshots = relationship("ProductSnapshot", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("ModerationComment", back_populates="task", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_tasks_status', 'status'),
        Index('idx_tasks_queue_priority', 'queue_priority'),
        Index('idx_tasks_assigned_moderator', 'assigned_moderator_id'),
        Index('idx_tasks_product_id', 'product_id'),
        Index('idx_tasks_status_queue_created', 'status', 'queue_priority', 'created_at'),
    )