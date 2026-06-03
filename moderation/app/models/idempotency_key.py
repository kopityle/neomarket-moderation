from sqlalchemy import Column, String, DateTime
from app.models.base import BaseModel
import uuid


class IdempotencyKey(BaseModel):
    __tablename__ = "idempotency_keys"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(36), unique=True, nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=False, index=True)