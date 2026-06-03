from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid


class ModerationComment(BaseModel):
    __tablename__ = "moderation_comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("moderation_tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # ← UUID модератора или продавца
    message = Column(Text, nullable=False)
    is_from_moderator = Column(Boolean, nullable=False)
    
    # Relationships
    task = relationship("ModerationTask", back_populates="comments")