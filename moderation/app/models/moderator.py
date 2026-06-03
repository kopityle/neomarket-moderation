# app/models/moderator.py
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from enum import Enum

from app.core.base import Base

class ModeratorRole(str, Enum):
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"

class Moderator(Base):
    __tablename__ = "moderators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    role = Column(SQLEnum(ModeratorRole), default=ModeratorRole.MODERATOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    category_specializations = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)

    def __repr__(self): 
        return f"<Moderator {self.email}>"