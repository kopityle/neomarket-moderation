from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ModerationDecision(BaseModel):
    __tablename__ = "moderation_decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("moderation_tasks.id", ondelete="CASCADE"), nullable=False)
    moderator_id = Column(String(36), nullable=False)  # UUID модератора из Auth
    decision = Column(String(20), nullable=False)  # APPROVED, DECLINED
    blocking_reason_id = Column(Integer, ForeignKey("blocking_reasons.id"), nullable=True)
    comment = Column(Text, nullable=True)
    
    # Relationships
    task = relationship("ModerationTask", back_populates="decisions")
    reason = relationship("BlockingReason", back_populates="decisions")