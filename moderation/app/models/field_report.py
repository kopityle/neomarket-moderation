from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel
import uuid


class FieldReport(BaseModel):
    __tablename__ = "field_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    field_path = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), default="ERROR")
    sku_id = Column(UUID(as_uuid=True), nullable=True)  # ← тоже UUID (внешний ключ к SKU из B2B)