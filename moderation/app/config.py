import os
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()


class Settings:
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "postgres")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "neomarket_moderation")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASS: str = os.getenv("DB_PASS", "postgres")
    
    # B2B Service
    B2B_SERVICE_URL: str = os.getenv("B2B_SERVICE_URL", "http://b2b-service:8000")
    B2B_TIMEOUT: int = int(os.getenv("B2B_TIMEOUT", "30"))
    B2B_SERVICE_KEY: str = os.getenv("B2B_SERVICE_KEY", "")  # ← ОБЯЗАТЕЛЬНО!
    
    # Auth
    BYPASS_AUTH: bool = os.getenv("BYPASS_AUTH", "True").lower() == "true"
    
    # Moderation settings
    TICKET_TTL_MINUTES: int = int(os.getenv("TICKET_TTL_MINUTES", "30"))  # TTL блокировки IN_REVIEW
    IDEMPOTENCY_TTL_HOURS: int = int(os.getenv("IDEMPOTENCY_TTL_HOURS", "24"))  # TTL idempotency_key
    
    # Queue settings
    DEFAULT_QUEUE_PRIORITY: int = int(os.getenv("DEFAULT_QUEUE_PRIORITY", "3"))
    MAX_QUEUE_PRIORITY: int = 4
    MIN_QUEUE_PRIORITY: int = 1
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def is_auth_bypassed(self) -> bool:
        """Проверка, отключена ли аутентификация (для разработки)"""
        return self.BYPASS_AUTH


settings = Settings()