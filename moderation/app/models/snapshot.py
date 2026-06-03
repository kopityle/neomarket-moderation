from sqlalchemy import Column, String, DateTime, ForeignKey, Index, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid


class SnapshotType:
    BEFORE = "BEFORE"
    AFTER = "AFTER"


class ProductSnapshot(BaseModel):
    __tablename__ = "product_snapshots"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("moderation_tasks.id", ondelete="CASCADE"), nullable=False)
    
    snapshot_type = Column(String(20), nullable=False)  # BEFORE или AFTER
    data = Column(JSON, nullable=False)
    
    # Relationships
    task = relationship("ModerationTask", back_populates="snapshots")
    
    __table_args__ = (
        Index('idx_snapshot_task_type', 'task_id', 'snapshot_type'),
    )