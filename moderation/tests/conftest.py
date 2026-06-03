# app/tests/conftest.py
import sys
import os

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.task import ModerationTask  # ← только модель!
from app.models.snapshot import ProductSnapshot, SnapshotType
from app.models.idempotency_key import IdempotencyKey
from app.models.reason import BlockingReason
from app.schemas.task import TaskStatus, TaskKind  # ← Pydantic схемы
from app.config import settings


# ==================== Test Database Setup ====================

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override dependency для тестов"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# ==================== Fixtures ====================

@pytest.fixture(autouse=True, scope="session")
def setup_database():
    """Создаём таблицы и заполняем начальными данными"""
    Base.metadata.create_all(bind=engine)
    
    # Добавляем тестовые причины блокировки
    db = TestingSessionLocal()
    try:
        reasons = [
            {"code": "WRONG_PHOTOS", "title": "Неверные фотографии", "hard_block": False},
            {"code": "INCORRECT_CATEGORY", "title": "Неверная категория", "hard_block": False},
            {"code": "FORBIDDEN_GOODS", "title": "Запрещённый товар", "hard_block": True},
        ]
        for r in reasons:
            existing = db.query(BlockingReason).filter(BlockingReason.code == r["code"]).first()
            if not existing:
                reason = BlockingReason(
                    code=r["code"],
                    title=r["title"],
                    hard_block=r["hard_block"],
                    is_active=True
                )
                db.add(reason)
        db.commit()
    finally:
        db.close()
    
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Фикстура для прямого доступа к БД"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def api_client():
    """Фикстура для HTTP-клиента"""
    return client


@pytest.fixture
def valid_service_key():
    """Валидный сервисный ключ из настроек"""
    return settings.B2B_SERVICE_KEY


@pytest.fixture
def product_id():
    return uuid4()


@pytest.fixture
def seller_id():
    return uuid4()


@pytest.fixture
def idempotency_key():
    return uuid4()


@pytest.fixture
def moderator_id():
    return uuid4()


@pytest.fixture
def test_blocking_reasons(db_session):
    """Фикстура: тестовые причины блокировки"""
    reasons_data = [
        ("WRONG_PHOTOS", "Неверные фотографии", False),
        ("INCORRECT_CATEGORY", "Неверная категория", False),
        ("FORBIDDEN_GOODS", "Запрещённый товар", True),
    ]
    
    reasons = []
    for code, title, hard_block in reasons_data:
        reason = BlockingReason(
            code=code,
            title=title,
            hard_block=hard_block,
            is_active=True
        )
        db_session.add(reason)
        reasons.append(reason)
    
    db_session.commit()
    
    for reason in reasons:
        db_session.refresh(reason)
    
    return reasons


# ==================== Helper Functions ====================

def create_test_ticket(db, product_id, seller_id, status=TaskStatus.PENDING, kind=TaskKind.CREATE):
    """Создать тестовый тикет"""
    ticket = ModerationTask(
        product_id=str(product_id),
        seller_id=str(seller_id),
        kind=kind.value,  # ← .value для Enum
        status=status.value,  # ← .value для Enum
        queue_priority=3,
        json_after={"title": "Test Product", "skus": []},
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def create_test_snapshot(db, task_id, snapshot_type, data):
    """Создать тестовый снапшот"""
    snapshot = ProductSnapshot(
        task_id=str(task_id),
        snapshot_type=snapshot_type.value if hasattr(snapshot_type, 'value') else snapshot_type,
        data=data,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot