from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Database
    database_url: str = "postgresql://postgres:postgres@postgres:5432/neomarket_moderation"
    
    # B2B Service
    b2b_service_url: str = "http://b2b-service:8000"
    b2b_timeout: int = 30
    
    # Auth
    bypass_auth: bool = True
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # игнорировать лишние поля


settings = Settings()