from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ProductSnapshot(BaseModel):
    __tablename__ = "product_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("moderation_tasks.id", ondelete="CASCADE"), nullable=False)
    
    product_data = Column(JSON, nullable=False)  # полная копия товара + SKU
    version = Column(Integer, default=1)
    is_initial = Column(Boolean, default=True)  # true = первая версия, false = после изменений
    
    # Relationships
    task = relationship("ModerationTask", back_populates="snapshots")