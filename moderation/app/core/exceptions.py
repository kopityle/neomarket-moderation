# app/core/exceptions.py
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from typing import Union


class AppException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(status_code=status_code, detail=message)


def format_error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Форматирует ошибку согласно OpenAPI схеме Error"""
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": None
        }
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return format_error_response(exc.status_code, exc.code, exc.message)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Конвертирует стандартное HTTPException в формат OpenAPI"""
    # Маппинг status_code → code
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


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Обработчик ValidationError (Pydantic)"""
    return format_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request validation failed"
    )