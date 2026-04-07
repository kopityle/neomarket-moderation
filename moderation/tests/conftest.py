import sys
import os
sys.path.insert(0, '/app')

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models import (
    ModerationTask,
    ProductSnapshot,
    ModerationDecision,
    BlockingReason,
    ModerationComment
)

# Тестовая БД (SQLite в памяти)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Создание таблиц один раз для всех тестов"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(setup_database):
    """Фикстура для сессии БД"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session):
    """Фикстура для тестового клиента"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_moderator_id():
    """Фикстура: ID модератора"""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def test_seller_id():
    """Фикстура: ID продавца"""
    return "660e8400-e29b-41d4-a716-446655440001"


@pytest.fixture
def test_blocking_reasons(db_session):
    """Фикстура: причины блокировки (только если их ещё нет)"""
    from app.models.reason import BlockingReason
    
    reasons_data = [
        ("wrong_photos", "Неверные фотографии", "Фотографии не соответствуют товару"),
        ("incorrect_category", "Неверная категория", "Товар размещён в неподходящей категории"),
        ("wrong_price", "Неверная цена", "Цена явно завышена или занижена"),
    ]
    
    reasons = []
    for code, name, desc in reasons_data:
        # Проверяем, существует ли уже такая причина
        existing = db_session.query(BlockingReason).filter(BlockingReason.code == code).first()
        if existing:
            reasons.append(existing)
        else:
            reason = BlockingReason(
                code=code,
                name=name,
                description=desc,
                is_active=True
            )
            db_session.add(reason)
            reasons.append(reason)
    
    db_session.commit()
    
    # Обновляем объекты
    for reason in reasons:
        db_session.refresh(reason)
    
    return reasons


@pytest.fixture
def test_moderation_task(db_session, test_seller_id):
    """Фикстура: задача на модерацию"""
    task = ModerationTask(
        product_id=1,
        seller_id=test_seller_id,
        priority=0,
        status="PENDING"
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def test_moderation_task_in_progress(db_session, test_seller_id, test_moderator_id):
    """Фикстура: задача в процессе модерации"""
    task = ModerationTask(
        product_id=2,
        seller_id=test_seller_id,
        priority=0,
        status="IN_PROGRESS",
        assigned_to=test_moderator_id
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task