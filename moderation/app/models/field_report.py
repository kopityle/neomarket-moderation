# app/models/field_report.py
from sqlalchemy import Column, String, Text
from app.models.base import BaseModel
import uuid


class FieldReport(BaseModel):
    __tablename__ = "field_reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), nullable=False, index=True)
    field_path = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), default="ERROR")
    sku_id = Column(String(36), nullable=True)