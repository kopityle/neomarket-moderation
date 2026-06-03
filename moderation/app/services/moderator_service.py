# app/services/moderator_service.py
from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from uuid import UUID, uuid4
from datetime import datetime
import bcrypt

from app.models.moderator import Moderator, ModeratorRole
from app.schemas.moderator import ModeratorCreateRequest, ModeratorUpdateRequest


class ModeratorAdminService:
    def __init__(self, db: Session):
        self.db = db

    def list_moderators(
        self,
        limit: int = 20,
        offset: int = 0,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Moderator], int]:
        """Список модераторов."""
        query = self.db.query(Moderator)

        if is_active is not None:
            query = query.filter(Moderator.is_active == is_active)

        total_count = query.count()
        moderators = query.offset(offset).limit(limit).all()

        return moderators, total_count

    def get_moderator(self, moderator_id: UUID) -> Optional[Moderator]:
        """Получить модератора по ID."""
        return self.db.query(Moderator).filter(Moderator.id == moderator_id).first()

    def get_moderator_by_email(self, email: str) -> Optional[Moderator]:
        """Получить модератора по email."""
        return self.db.query(Moderator).filter(Moderator.email == email).first()

    def create_moderator(self, request: ModeratorCreateRequest) -> Moderator:
        """Создать нового модератора."""
        password_hash = bcrypt.hashpw(
            request.password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        moderator = Moderator(
            id=uuid4(),
            email=request.email,
            password_hash=password_hash,
            first_name=request.first_name,
            last_name=request.last_name,
            role=request.role,
            category_specializations=[str(cid) for cid in request.category_specializations],
            is_active=True,
        )

        self.db.add(moderator)
        self.db.commit()
        self.db.refresh(moderator)

        return moderator

    def update_moderator(
        self,
        moderator_id: UUID,
        request: ModeratorUpdateRequest
    ) -> Optional[Moderator]:
        """Обновить данные модератора."""
        moderator = self.get_moderator(moderator_id)
        if not moderator:
            return None

        if request.first_name is not None:
            moderator.first_name = request.first_name
        if request.last_name is not None:
            moderator.last_name = request.last_name
        if request.role is not None:
            moderator.role = request.role
        if request.is_active is not None:
            moderator.is_active = request.is_active
        if request.category_specializations is not None:
            moderator.category_specializations = [str(cid) for cid in request.category_specializations]

        moderator.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(moderator)

        return moderator

    def deactivate_moderator(self, moderator_id: UUID) -> bool:
        """Деактивировать модератора (soft-delete)."""
        moderator = self.get_moderator(moderator_id)
        if not moderator:
            return False

        moderator.is_active = False
        moderator.updated_at = datetime.utcnow()
        self.db.commit()

        return True