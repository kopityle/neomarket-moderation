from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel
import uuid


class IdempotencyKey(BaseModel):
    __tablename__ = "idempotency_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(36), unique=True, nullable=False, index=True)  # ← key остаётся String (это строка извне)
    processed_at = Column(DateTime(timezone=True), nullable=False, index=True)