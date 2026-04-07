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
    
    # Auth
    BYPASS_AUTH: bool = os.getenv("BYPASS_AUTH", "True").lower() == "true"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()