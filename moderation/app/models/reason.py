from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class BlockingReason(BaseModel):
    __tablename__ = "blocking_reasons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # INTEGER (справочник)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    decisions = relationship("ModerationDecision", back_populates="reason")