# app/models/refresh_token.py
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from datetime import datetime
import uuid

from app.core.base import Base

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(255), unique=True, nullable=False, index=True)
    moderator_id = Column(PG_UUID(as_uuid=True), ForeignKey("moderators.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<RefreshToken moderator_id={self.moderator_id}>"