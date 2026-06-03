# tests/conftest.py
import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import get_db
from app.database import Base  # Импортируем Base ИЗ database.py!
from app.config import settings

# КРИТИЧЕСКИ ВАЖНО: Импортируем все модели для регистрации в Base
from app.models.moderator import Moderator
from app.models.reason import BlockingReason
from app.models.task import ModerationTask
from app.models.snapshot import ProductSnapshot
from app.models.idempotency_key import IdempotencyKey
from app.models.refresh_token import RefreshToken
from app.models.field_report import FieldReport
from app.models.comment import ModerationComment


# ==================== Test Database Setup ====================

def get_test_engine():
    """Создаёт engine для тестовой БД - PostgreSQL"""
    database_url = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@postgres_test:5432/neomarket_moderation_test")
    print(f"🐘 Using PostgreSQL for tests: {database_url}")
    return create_engine(database_url, poolclass=NullPool)


engine = get_test_engine()
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ==================== DB setup ====================

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Создаёт таблицы в БД перед тестами и очищает после"""
    print("📦 Creating all tables...")
    
    # Проверяем зарегистрированные модели
    print(f"Registered tables: {list(Base.metadata.tables.keys())}")
    
    # СОЗДАЁМ ТАБЛИЦЫ
    Base.metadata.create_all(bind=engine)
    
    # Проверяем результат
    from sqlalchemy import inspect
    inspector = inspect(engine)
    print(f"Tables in DB: {inspector.get_table_names()}")
    
    print("✅ Tables created successfully!")
    
    yield
    
    print("🧹 Dropping all tables...")
    Base.metadata.drop_all(bind=engine, checkfirst=True)


# ==================== Transaction per test ====================

@pytest.fixture
def db_session():
    """Фикстура для сессии БД с транзакцией на тест"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


# ==================== Test client ====================

@pytest.fixture
def api_client(db_session):
    """Фикстура для HTTP-клиента"""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ==================== Auth fixtures ====================

@pytest.fixture
def admin_moderator(db_session):
    """Создаёт ADMIN модератора для тестов"""
    import bcrypt
    
    moderator = Moderator(
        id=uuid4(),
        email="admin@test.com",
        password_hash=bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        first_name="Admin",
        role="ADMIN",
        is_active=True,
        category_specializations=[],
    )
    db_session.add(moderator)
    db_session.commit()
    db_session.refresh(moderator)
    return moderator


@pytest.fixture
def regular_moderator(db_session):
    """Создаёт обычного модератора для тестов"""
    import bcrypt
    
    moderator = Moderator(
        id=uuid4(),
        email="moderator@test.com",
        password_hash=bcrypt.hashpw("mod123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        first_name="Moderator",
        role="MODERATOR",
        is_active=True,
        category_specializations=[],
    )
    db_session.add(moderator)
    db_session.commit()
    db_session.refresh(moderator)
    return moderator


@pytest.fixture
def admin_moderator_id(admin_moderator):
    return admin_moderator.id


@pytest.fixture
def regular_moderator_id(regular_moderator):
    return regular_moderator.id


@pytest.fixture
def moderator_headers(admin_moderator):
    return {"X-Moderator-Id": str(admin_moderator.id)}


# ==================== Simple fixtures ====================

@pytest.fixture
def valid_service_key():
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
def test_reason(db_session):
    reason = BlockingReason(
        id=uuid4(),
        code="TEST_CRUD_REASON",
        title="Test CRUD Reason",
        description="Original description",
        hard_block=False,
        is_active=True,
    )
    db_session.add(reason)
    db_session.commit()
    db_session.refresh(reason)
    return reason