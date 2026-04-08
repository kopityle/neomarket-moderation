from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid


class ModerationComment(BaseModel):
    __tablename__ = "moderation_comments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("moderation_tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), nullable=False)  # кто написал (модератор или продавец)
    message = Column(Text, nullable=False)
    is_from_moderator = Column(Boolean, nullable=False)  # true = от модератора, false = от продавца
    
    # Relationships
    task = relationship("ModerationTask", back_populates="comments")