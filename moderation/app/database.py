# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.core.base import Base
import os

# Определяем, в тестовом режиме мы или нет
IS_TESTING = os.getenv("PYTEST_CURRENT_TEST") is not None or os.getenv("ENV") == "test"

if IS_TESTING:
    # Для тестов используем тестовую БД
    DATABASE_URL = os.getenv(
        "TEST_DATABASE_URL", 
        f"postgresql://{settings.DB_USER}:{settings.DB_PASS}@postgres_test:5432/neomarket_moderation_test"
    )
else:
    # Для обычного режима - основная БД
    DATABASE_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASS}@" \
                   f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Создание engine
engine = create_engine(DATABASE_URL)

# Создание сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency для FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()