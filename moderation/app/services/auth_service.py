# app/services/auth_service.py
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import jwt
import bcrypt
from typing import Optional

from app.models.moderator import Moderator
from app.models.refresh_token import RefreshToken
from app.config import settings


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def authenticate(self, email: str, password: str) -> Optional[Moderator]:
        """Аутентификация модератора."""
        moderator = self.db.query(Moderator).filter(
            Moderator.email == email,
            Moderator.is_active == True
        ).first()

        if not moderator:
            return None

        if not bcrypt.checkpw(password.encode('utf-8'), moderator.password_hash.encode('utf-8')):
            return None

        # Обновляем время последнего входа
        moderator.last_login_at = datetime.utcnow()
        self.db.commit()

        return moderator

    def create_access_token(self, moderator_id: UUID) -> str:
        """Создать access token."""
        expires_delta = timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS)
        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": str(moderator_id),
            "exp": expire,
            "type": "access"
        }

        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_refresh_token(self, moderator_id: UUID) -> str:
        """Создать refresh token и сохранить в БД."""
        token = str(uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRE_SECONDS)

        db_token = RefreshToken(
            token=token,
            moderator_id=moderator_id,
            expires_at=expires_at
        )
        self.db.add(db_token)
        self.db.commit()

        return token

    def validate_refresh_token(self, token: str) -> Optional[UUID]:
        """Проверить refresh token и вернуть moderator_id."""
        db_token = self.db.query(RefreshToken).filter(
            RefreshToken.token == token,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.utcnow()
        ).first()

        if not db_token:
            return None

        return db_token.moderator_id

    def revoke_refresh_token(self, token: str) -> None:
        """Отозвать refresh token."""
        db_token = self.db.query(RefreshToken).filter(
            RefreshToken.token == token,
            RefreshToken.revoked_at.is_(None)
        ).first()

        if db_token:
            db_token.revoked_at = datetime.utcnow()
            self.db.commit()

    def get_moderator(self, moderator_id: UUID) -> Optional[Moderator]:
        """Получить модератора по ID."""
        return self.db.query(Moderator).filter(Moderator.id == moderator_id).first()