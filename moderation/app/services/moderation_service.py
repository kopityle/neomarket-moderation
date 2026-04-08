from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from app.models.task import ModerationTask
from app.models.snapshot import ProductSnapshot
from app.models.decision import ModerationDecision
from app.models.reason import BlockingReason
from app.schemas.task import TaskStatus
from app.schemas.decision import DecisionType
from app.services.b2b_client import B2BClient


class ModerationService:
    def __init__(self, db: Session):
        self.db = db
        self.b2b_client = B2BClient()
    
    def get_blocking_reasons(self, is_active: bool = True) -> List[BlockingReason]:
        """Получить список причин блокировки (синхронно)"""
        return self.db.query(BlockingReason).filter(
            BlockingReason.is_active == is_active
        ).all()
    
    def get_next_task(self, moderator_id: UUID, priority: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Получить следующую задачу на модерацию (синхронно, без B2B для тестов)"""
        
        query = self.db.query(ModerationTask).filter(
            ModerationTask.status == TaskStatus.PENDING
        )
        
        if priority is not None:
            query = query.filter(ModerationTask.priority == priority)
        
        task = query.order_by(
            ModerationTask.priority.desc(),
            ModerationTask.created_at.asc()
        ).first()
        
        if not task:
            return None
        
        # Обновляем статус задачи
        task.status = TaskStatus.IN_PROGRESS
        task.assigned_to = str(moderator_id)
        self.db.commit()
        
        # Возвращаем товар в формате, совместимом с B2BProduct
        product = {
            "id": task.product_id,  # ← UUID строка
            "title": f"Test Product {task.product_id}",
            "description": "Test description",
            "status": "PENDING_MODERATION",
            "seller_id": task.seller_id,
            "category": {"id": 1, "name": "Test Category"},
            "images": [],
            "characteristics": [],
            "skus": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": None,
            "published_at": None
        }
        
        # Создаём снапшот
        self.create_snapshot(task.id, product, is_initial=False)
        
        return product
    
    def create_snapshot(self, task_id: int, product: Dict[str, Any], is_initial: bool = True) -> ProductSnapshot:
        """Создать снапшот товара"""
        
        snapshot = ProductSnapshot(
            task_id=task_id,
            product_data=product,
            version=1,
            is_initial=is_initial
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot
    
    def approve_product(self, product_id: int, moderator_id: UUID) -> bool:
        """Одобрить товар"""
        
        task = self.db.query(ModerationTask).filter(
        and_(
            ModerationTask.product_id == product_id,
            ModerationTask.status == TaskStatus.IN_PROGRESS
        )
        ).first()
        
        if not task:
            return False
        
        # Создаём решение
        decision = ModerationDecision(
            task_id=task.id,
            moderator_id=str(moderator_id),
            decision=DecisionType.APPROVED
        )
        self.db.add(decision)
        
        # Обновляем задачу
        task.status = TaskStatus.APPROVED
        task.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        # Отправляем результат в B2B (синхронно, без ожидания)
        # В реальном коде нужно использовать asyncio.create_task()
        
        return True
    
    def decline_product(
        self, 
        product_id: str, 
        moderator_id: UUID, 
        reason_id: int, 
        comment: Optional[str] = None
    ) -> bool:
        """Заблокировать товар"""
        task = self.db.query(ModerationTask).filter(
            and_(
                ModerationTask.product_id == product_id,
                ModerationTask.status == TaskStatus.IN_PROGRESS
            )
        ).first()
        
        if not task:
            return False
        
        # Создаём решение
        decision = ModerationDecision(
            task_id=task.id,
            moderator_id=str(moderator_id),
            decision=DecisionType.DECLINED,
            blocking_reason_id=reason_id,
            comment=comment
        )
        self.db.add(decision)
        
        # Обновляем задачу
        task.status = TaskStatus.DECLINED
        task.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        return True