from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Integer
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid


class ProductSnapshot(BaseModel):
    __tablename__ = "product_snapshots"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("moderation_tasks.id", ondelete="CASCADE"), nullable=False)
    
    product_data = Column(JSON, nullable=False)  # полная копия товара + SKU
    version = Column(Integer, default=1)
    is_initial = Column(Boolean, default=True)  # true = первая версия, false = после изменений
    
    # Relationships
    task = relationship("ModerationTask", back_populates="snapshots")