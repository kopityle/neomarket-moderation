from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from starlette.responses import JSONResponse

from app.api import router as api_router
from app.core.logger import setup_logging
from app.scheduler import scheduler
from app.core.exceptions import AppException, format_error_response


# Настройка логирования
setup_logging()


# ==================== ОБРАБОТЧИКИ ОШИБОК ====================

async def app_exception_handler(request, exc: AppException) -> JSONResponse:
    """Обработчик кастомных исключений AppException"""
    return format_error_response(exc.status_code, exc.code, exc.message)


async def http_exception_handler(request, exc: HTTPException) -> JSONResponse:
    """Конвертирует стандартное HTTPException в формат OpenAPI"""
    code_map = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    }
    
    code = code_map.get(exc.status_code, "INTERNAL_ERROR")
    message = exc.detail if exc.detail else "An error occurred"
    
    return format_error_response(exc.status_code, code, message)


async def validation_exception_handler(request, exc: RequestValidationError) -> JSONResponse:
    """Обработчик ошибок валидации Pydantic"""
    return format_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request validation failed"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Регистрируем обработчики ошибок
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
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
    lifespan=lifespan
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