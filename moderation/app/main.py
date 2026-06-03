from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import router as api_router
from app.core.logger import setup_logging
from app.scheduler import scheduler  # ← добавить


# Настройка логирования
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Запуск при старте
    print("Starting Moderation Service...")
    scheduler.start()
    print("Scheduler started (expired tickets will be released every 5 minutes)")
    
    yield
    
    # Остановка при завершении
    print("Shutting down Moderation Service...")
    scheduler.shutdown()
    print("Scheduler stopped")


# Создание приложения с lifespan
app = FastAPI(
    title="NeoMarket Moderation Service",
    description="Сервис модерации товаров: проверка, одобрение, блокировка",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan  # ← добавить
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем единый роутер
app.include_router(api_router)


@app.get("/")
async def root():
    """Корневой endpoint с информацией о сервисе"""
    return {
        "service": "NeoMarket Moderation",
        "version": "0.1.0",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "ok",
        "service": "moderation",
        "database": "connected"
    }