# app/services/moderation_service.py
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from app.models.task import ModerationTask
from app.models.snapshot import ProductSnapshot
from app.models.reason import BlockingReason
from app.models.idempotency_key import IdempotencyKey
from app.schemas.task import TaskStatus, TaskKind
from app.schemas.decision import FieldReport
from app.schemas.snapshot import SnapshotType
from app.schemas.b2b import (
    IncomingB2BEvent, EventProductCreated, EventProductEdited, EventProductDeleted,
    ModerationEventRequest, ModerationEventType, FieldReport as B2BFieldReport  # ← добавить
)
from app.config import settings
from app.schemas.stats import StatsOverview, ModeratorStats
from app.services.b2b_client import B2BClient


class ModerationService:
    def __init__(self, db: Session):
        self.db = db
        self.b2b_client = B2BClient()
    
    # ==================== B2B EVENTS ====================
    
    def process_b2b_event(self, event: IncomingB2BEvent) -> bool:
        """Обработать входящее событие от B2B."""
        # 1. Проверка идемпотентности
        if self._is_idempotency_key_used(event.idempotency_key):
            return False
        
        # 2. Обработка по типу события
        if event.event_type == "PRODUCT_CREATED":
            payload = EventProductCreated(**event.payload)
            self._handle_product_created(payload)
        elif event.event_type == "PRODUCT_EDITED":
            payload = EventProductEdited(**event.payload)
            self._handle_product_edited(payload)
        elif event.event_type == "PRODUCT_DELETED":
            payload = EventProductDeleted(**event.payload)
            self._handle_product_deleted(payload)
        else:
            return True
        
        # 3. Сохраняем ключ идемпотентности
        self._save_idempotency_key(event.idempotency_key)
        
        return True
    
    def _is_idempotency_key_used(self, key: UUID) -> bool:
        """Проверить, не использовался ли уже ключ идемпотентности."""
        cutoff = datetime.utcnow() - timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS)
        record = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.key == str(key),
            IdempotencyKey.processed_at >= cutoff
        ).first()
        return record is not None
    
    def _save_idempotency_key(self, key: UUID) -> None:
        """Сохранить использованный ключ идемпотентности."""
        db_key = IdempotencyKey(
            key=str(key),
            processed_at=datetime.utcnow()
        )
        self.db.add(db_key)
        self.db.commit()
    
    def _handle_product_created(self, payload: EventProductCreated) -> None:
        """Обработка CREATED события."""
        existing = self.db.query(ModerationTask).filter(
            ModerationTask.product_id == str(payload.product_id)
        ).first()
        
        if existing and existing.status == TaskStatus.HARD_BLOCKED:
            return
        
        cleaned_json = self._strip_private_fields(payload.json_after)
        
        ticket = ModerationTask(
            product_id=str(payload.product_id),
            seller_id=str(payload.seller_id),
            kind=TaskKind.CREATE,
            status=TaskStatus.PENDING,
            queue_priority=payload.queue_priority,
            category_id=str(payload.category_id) if payload.category_id else None,
            json_after=cleaned_json,
        )
        self.db.add(ticket)
        self.db.flush()
        
        snapshot = ProductSnapshot(
            task_id=str(ticket.id),
            snapshot_type=SnapshotType.AFTER,
            data=cleaned_json,
        )
        self.db.add(snapshot)
        
        self.db.commit()
    
    def _handle_product_edited(self, payload: EventProductEdited) -> None:
        """Обработка EDITED события"""
        ticket = self.db.query(ModerationTask).filter(
            ModerationTask.product_id == str(payload.product_id)
        ).first()
        
        if not ticket:
            return
        
        if ticket.status == TaskStatus.HARD_BLOCKED:
            return
        
        old_status = ticket.status
        
        before_snapshot = ProductSnapshot(
            task_id=ticket.id,
            snapshot_type=SnapshotType.BEFORE,
            data=ticket.json_after,
        )
        self.db.add(before_snapshot)
        
        cleaned_json = self._strip_private_fields(payload.json_after)
        ticket.json_after = cleaned_json
        
        ticket.status = TaskStatus.PENDING
        ticket.assigned_moderator_id = None
        ticket.claimed_at = None
        ticket.claim_expires_at = None
        ticket.queue_priority = self._calculate_queue_priority(old_status, cleaned_json)
        ticket.updated_at = datetime.utcnow()
        
        after_snapshot = ProductSnapshot(
            task_id=ticket.id,
            snapshot_type=SnapshotType.AFTER,
            data=cleaned_json,
        )
        self.db.add(after_snapshot)
        
        self.db.commit()
    
    def _handle_product_deleted(self, payload: EventProductDeleted) -> None:
        """Обработка DELETED события."""
        ticket = self.db.query(ModerationTask).filter(
            ModerationTask.product_id == str(payload.product_id)
        ).first()
        
        if not ticket:
            return
        
        self.db.delete(ticket)
        self.db.commit()
    
    def _strip_private_fields(self, product_data: dict) -> dict:
        """Удалить приватные поля продавца (cost_price, reserved_quantity)."""
        product_data = {**product_data}
        for sku in product_data.get('skus', []):
            sku.pop('cost_price', None)
            sku.pop('reserved_quantity', None)
        return product_data
    
    def _calculate_queue_priority(self, old_status: TaskStatus, json_after: dict) -> int:
        """Вычислить приоритет очереди."""
        if old_status == TaskStatus.BLOCKED:
            return 2
        
        has_stock = self._has_active_stock(json_after)
        
        if old_status == TaskStatus.APPROVED:
            return 3 if has_stock else 4
        
        return 1
    
    def _has_active_stock(self, json_after: dict) -> bool:
        """Проверить наличие SKU с active_quantity > 0."""
        for sku in json_after.get("skus", []):
            if sku.get("active_quantity", 0) > 0:
                return True
        return False
    
    # ==================== QUEUE ====================
    
    def get_queue(
        self,
        limit: int = 20,
        offset: int = 0,
        queue_priority: Optional[int] = None,
        category_id: Optional[UUID] = None,
        seller_id: Optional[UUID] = None,
    ) -> Tuple[List[ModerationTask], int]:
        """Получить очередь PENDING-тикетов."""
        query = self.db.query(ModerationTask).filter(
            ModerationTask.status == TaskStatus.PENDING
        )
        
        if queue_priority is not None:
            query = query.filter(ModerationTask.queue_priority == queue_priority)
        if category_id is not None:
            query = query.filter(ModerationTask.category_id == str(category_id))
        if seller_id is not None:
            query = query.filter(ModerationTask.seller_id == str(seller_id))
        
        total_count = query.count()
        
        tickets = query.order_by(
            asc(ModerationTask.queue_priority),
            asc(ModerationTask.created_at)
        ).offset(offset).limit(limit).all()
        
        return tickets, total_count
    
    def get_moderator_active_ticket(self, moderator_id: UUID) -> Optional[ModerationTask]:
        """Получить активный IN_REVIEW тикет модератора (не истёкший)"""
        return self.db.query(ModerationTask).filter(
            ModerationTask.assigned_moderator_id == str(moderator_id),
            ModerationTask.status == TaskStatus.IN_REVIEW,
            ModerationTask.claim_expires_at > datetime.utcnow()
        ).first()
    
    def get_ticket_by_id(self, ticket_id: UUID) -> Optional[ModerationTask]:
        """Получить тикет по ID без проверки прав"""
        return self.db.query(ModerationTask).filter(
            ModerationTask.id == str(ticket_id)
        ).first()
    
    def claim_next_ticket(
        self,
        moderator_id: UUID,
        queue_priority: Optional[int] = None,
        category_ids: Optional[List[UUID]] = None,
    ) -> Optional[ModerationTask]:
        """Атомарно взять следующий тикет в работу."""
        from sqlalchemy import asc
        
        active_ticket = self.get_moderator_active_ticket(moderator_id)
        if active_ticket:
            return None
        
        priorities_to_try = [queue_priority] if queue_priority else [1, 2, 3, 4]
        
        ticket = None
        
        for priority in priorities_to_try:
            query = self.db.query(ModerationTask).filter(
                ModerationTask.status == TaskStatus.PENDING,
                ModerationTask.queue_priority == priority
            )
            
            if category_ids:
                query = query.filter(ModerationTask.category_id.in_([str(cid) for cid in category_ids]))
            
            ticket = query.order_by(
                asc(ModerationTask.queue_priority),
                asc(ModerationTask.created_at)
            ).first()
            
            if ticket:
                break
        
        if not ticket:
            return None
        
        ticket.status = TaskStatus.IN_REVIEW
        ticket.assigned_moderator_id = str(moderator_id)
        ticket.claimed_at = datetime.utcnow()
        ticket.claim_expires_at = datetime.utcnow() + timedelta(minutes=settings.TICKET_TTL_MINUTES)
        
        self.db.commit()
        self.db.refresh(ticket)
        
        return ticket
    
    def get_ticket_for_moderation(self, ticket_id: UUID, moderator_id: UUID) -> Optional[ModerationTask]:
        """Получить тикет для модерации с проверкой прав"""
        return self.db.query(ModerationTask).filter(
            ModerationTask.id == str(ticket_id),
            ModerationTask.status == TaskStatus.IN_REVIEW,
            ModerationTask.assigned_moderator_id == str(moderator_id)
        ).first()
    
    def check_product_has_skus(self, product_id: UUID) -> bool:
        """Проверить, есть ли у товара SKU (через json_after)."""
        ticket = self.db.query(ModerationTask).filter(
            ModerationTask.product_id == str(product_id)
        ).first()
        
        if ticket and ticket.json_after:
            skus = ticket.json_after.get("skus", [])
            return len(skus) > 0
        
        return False
    
    def check_product_not_changed_during_review(self, ticket: ModerationTask) -> bool:
        """Проверить, что товар не был изменён во время ревью."""
        if ticket.claimed_at and ticket.updated_at:
            return ticket.updated_at <= ticket.claimed_at
        return True
    
    def release_ticket(self, ticket_id: UUID, moderator_id: UUID) -> Optional[ModerationTask]:
        """Вернуть тикет в очередь."""
        ticket = self.db.query(ModerationTask).filter(
            ModerationTask.id == str(ticket_id),
            ModerationTask.status == TaskStatus.IN_REVIEW,
            ModerationTask.assigned_moderator_id == str(moderator_id)
        ).first()
        
        if not ticket:
            return None
        
        ticket.status = TaskStatus.PENDING
        ticket.assigned_moderator_id = None
        ticket.claimed_at = None
        ticket.claim_expires_at = None
        
        self.db.commit()
        self.db.refresh(ticket)
        
        return ticket
    
    # ==================== TICKETS ====================
    
    def get_tickets(
        self,
        limit: int = 20,
        offset: int = 0,
        status: Optional[TaskStatus] = None,
        moderator_id: Optional[UUID] = None,
        product_id: Optional[UUID] = None,
        seller_id: Optional[UUID] = None,
        created_from: Optional[str] = None,
        created_to: Optional[str] = None,
    ) -> Tuple[List[ModerationTask], int]:
        """Получить список тикетов с фильтрацией."""
        query = self.db.query(ModerationTask)
        
        if status:
            query = query.filter(ModerationTask.status == status)
        if moderator_id:
            query = query.filter(ModerationTask.assigned_moderator_id == str(moderator_id))
        if product_id:
            query = query.filter(ModerationTask.product_id == str(product_id))
        if seller_id:
            query = query.filter(ModerationTask.seller_id == str(seller_id))
        
        total_count = query.count()
        tickets = query.order_by(desc(ModerationTask.created_at)).offset(offset).limit(limit).all()
        
        return tickets, total_count
    
    def get_ticket_detail(self, ticket_id: UUID) -> Optional[Dict[str, Any]]:
        """Получить детальную информацию о тикете."""
        ticket = self.db.query(ModerationTask).filter(ModerationTask.id == str(ticket_id)).first()
        
        if not ticket:
            return None
        
        snapshots = self.db.query(ProductSnapshot).filter(
            ProductSnapshot.task_id == str(ticket_id)
        ).all()
        
        json_before = None
        json_after = None
        
        for snapshot in snapshots:
            if snapshot.snapshot_type == SnapshotType.BEFORE:
                json_before = snapshot.data
            elif snapshot.snapshot_type == SnapshotType.AFTER:
                json_after = snapshot.data
        
        if json_after is None:
            json_after = ticket.json_after
        if json_before is None:
            json_before = ticket.json_before
        
        return {
            **ticket.__dict__,
            "json_before": json_before,
            "json_after": json_after,
        }
    
    def approve_ticket(
        self,
        ticket_id: UUID,
        moderator_id: UUID,
        comment: Optional[str] = None,
    ) -> Optional[ModerationTask]:
        """Одобрить тикет и отправить событие в B2B"""
        ticket = self.db.query(ModerationTask).filter(
            ModerationTask.id == str(ticket_id),
            ModerationTask.status == TaskStatus.IN_REVIEW,
            ModerationTask.assigned_moderator_id == str(moderator_id)
        ).first()
        
        if not ticket:
            return None
        
        ticket.status = TaskStatus.APPROVED
        ticket.decision_at = datetime.utcnow()
        ticket.decision_comment = comment
        ticket.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(ticket)
        
        self._send_moderation_event(ticket, "MODERATED")
        
        return ticket
    
    def _send_moderation_event(
        self, 
        ticket: ModerationTask, 
        event_type: str,
        blocking_reason_ids: List[UUID] = None,
        field_reports: Optional[List[B2BFieldReport]] = None  # ← используем B2BFieldReport
    ) -> None:
        """Отправить событие в B2B асинхронно"""
        hard_block = (event_type == "HARD_BLOCKED")
        
        event = ModerationEventRequest(
            idempotency_key=uuid4(),
            product_id=UUID(ticket.product_id),
            event_type=ModerationEventType.BLOCKED,
            moderator_id=UUID(ticket.assigned_moderator_id) if ticket.assigned_moderator_id else None,
            moderator_comment=ticket.decision_comment,
            blocking_reason_id=blocking_reason_ids[0] if blocking_reason_ids else None,
            hard_block=hard_block,
            field_reports=field_reports,  # ← напрямую
            occurred_at=datetime.utcnow(),
        )
        
        # ... отправка
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.b2b_client.send_moderation_event(event))
            else:
                asyncio.run(self.b2b_client.send_moderation_event(event))
        except RuntimeError:
            asyncio.run(self.b2b_client.send_moderation_event(event))
    

    def validate_blocking_reasons(self, reason_ids: List[UUID]) -> List[BlockingReason]:
        """Проверить, что все причины существуют"""
        reasons = self.db.query(BlockingReason).filter(
            BlockingReason.id.in_([str(rid) for rid in reason_ids]),
            BlockingReason.is_active == True
        ).all()
        
        if len(reasons) != len(reason_ids):
            return []
        return reasons


    def validate_field_reports(self, field_reports: List[FieldReport]) -> List[str]:
        """
        Проверить field_reports на допустимые field_path.
        Допустимые значения:
        - title, description, product_images, category
        - sku_name, sku_image, sku_price, sku_characteristics
        - images[0].url, images[0].alt (для конкретных изображений)
        - skus[0].name, skus[0].price и т.д.
        """
        allowed_base_fields = {
            "title", "description", "product_images", "category",
            "sku_name", "sku_image", "sku_price", "sku_characteristics"
        }
        
        invalid = []
        for report in field_reports:
            field = report.field_path
            
            # Проверка на точное совпадение
            if field in allowed_base_fields:
                continue
            
            # Проверка на pattern: images[数字].url или images[数字].alt
            import re
            if re.match(r'^images\[\d+\]\.(url|alt)$', field):
                continue
            
            # Проверка на pattern: skus[数字].field
            if re.match(r'^skus\[\d+\]\.(name|price|image|article|active_quantity)$', field):
                continue
            
            invalid.append(field)
        
        return invalid


    def save_field_reports(self, ticket_id: str, field_reports: Optional[List[FieldReport]]) -> None:
        """Сохранить field_reports в БД"""
        from app.models.field_report import FieldReport as FieldReportModel
        
        if not field_reports:
            return
        
        # Удаляем старые
        self.db.query(FieldReportModel).filter(
            FieldReportModel.task_id == ticket_id
        ).delete()
        
        # Сохраняем новые
        for report in field_reports:
            db_report = FieldReportModel(
                id=str(uuid4()),
                task_id=ticket_id,
                field_path=report.field_path,
                message=report.message,
                severity=report.severity,
                sku_id=str(report.sku_id) if report.sku_id else None,
            )
            self.db.add(db_report)
        
        self.db.commit()

    def block_ticket(
        self,
        ticket_id: UUID,
        moderator_id: UUID,
        blocking_reason_ids: List[UUID],
        comment: Optional[str] = None,
        field_reports: Optional[List[FieldReport]] = None,  # ← из app.schemas.decision
    ) -> Optional[ModerationTask]:
        """Заблокировать тикет (soft или hard)"""
        ticket = self.db.query(ModerationTask).filter(
            ModerationTask.id == str(ticket_id),
            ModerationTask.status == TaskStatus.IN_REVIEW,
            ModerationTask.assigned_moderator_id == str(moderator_id)
        ).first()
        
        if not ticket:
            return None
        
        # Получаем причины блокировки
        reasons = self.db.query(BlockingReason).filter(
            BlockingReason.id.in_([str(rid) for rid in blocking_reason_ids])
        ).all()
        
        has_hard_block = any(reason.hard_block for reason in reasons)
        
        if has_hard_block:
            ticket.status = TaskStatus.HARD_BLOCKED
            event_type = "HARD_BLOCKED"
        else:
            ticket.status = TaskStatus.BLOCKED
            event_type = "BLOCKED"
        
        ticket.decision_at = datetime.utcnow()
        ticket.decision_comment = comment
        ticket.updated_at = datetime.utcnow()
        ticket.blocking_reason_id = str(blocking_reason_ids[0]) if blocking_reason_ids else None
        
        # Сохраняем field_reports (SQLAlchemy модель)
        self.save_field_reports(ticket.id, field_reports)
        
        self.db.commit()
        self.db.refresh(ticket)
        
        # Конвертируем FieldReport из decision в B2BFieldReport для отправки
        b2b_reports = None
        if field_reports:
            b2b_reports = []
            for report in field_reports:
                b2b_reports.append(
                    B2BFieldReport(
                        field_path=report.field_path,
                        message=report.message,
                        severity=report.severity,
                        sku_id=report.sku_id,
                    )
                )
        
        # Отправляем событие в B2B (с B2BFieldReport)
        self._send_moderation_event(ticket, event_type, blocking_reason_ids, b2b_reports)
        
        return ticket
    # ==================== BLOCKING REASONS ====================
    
    def get_blocking_reasons(
        self,
        hard_block: Optional[bool] = None,
        is_active: bool = True,
    ) -> List[BlockingReason]:
        """Получить список причин блокировки с фильтрацией."""
        query = self.db.query(BlockingReason).filter(BlockingReason.is_active == is_active)
        
        if hard_block is not None:
            query = query.filter(BlockingReason.hard_block == hard_block)
        
        return query.all()
    
    # ==================== STATS ====================
    
    def get_stats_overview(self, period: str = "today") -> StatsOverview:
        """Получить сводку по очереди и решениям."""
        now = datetime.utcnow()
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        else:
            start_date = now - timedelta(days=30)
        
        pending_count = self.db.query(ModerationTask).filter(
            ModerationTask.status == TaskStatus.PENDING
        ).count()
        
        in_review_count = self.db.query(ModerationTask).filter(
            ModerationTask.status == TaskStatus.IN_REVIEW
        ).count()
        
        approved_count = self.db.query(ModerationTask).filter(
            ModerationTask.status == TaskStatus.APPROVED,
            ModerationTask.decision_at >= start_date
        ).count()
        
        blocked_count = self.db.query(ModerationTask).filter(
            ModerationTask.status == TaskStatus.BLOCKED,
            ModerationTask.decision_at >= start_date
        ).count()
        
        hard_blocked_count = self.db.query(ModerationTask).filter(
            ModerationTask.status == TaskStatus.HARD_BLOCKED,
            ModerationTask.decision_at >= start_date
        ).count()
        
        pending_by_priority = {
            "1": self.db.query(ModerationTask).filter(
                ModerationTask.status == TaskStatus.PENDING,
                ModerationTask.queue_priority == 1
            ).count(),
            "2": self.db.query(ModerationTask).filter(
                ModerationTask.status == TaskStatus.PENDING,
                ModerationTask.queue_priority == 2
            ).count(),
            "3": self.db.query(ModerationTask).filter(
                ModerationTask.status == TaskStatus.PENDING,
                ModerationTask.queue_priority == 3
            ).count(),
            "4": self.db.query(ModerationTask).filter(
                ModerationTask.status == TaskStatus.PENDING,
                ModerationTask.queue_priority == 4
            ).count(),
        }
        
        return StatsOverview(
            pending_count=pending_count,
            in_review_count=in_review_count,
            approved_count=approved_count,
            blocked_count=blocked_count,
            hard_blocked_count=hard_blocked_count,
            avg_review_time_seconds=None,
            pending_by_priority=pending_by_priority,
        )
    
    def get_moderator_stats(self, period: str = "week") -> List[ModeratorStats]:
        """Получить статистику по модераторам."""
        return []
    
    def _add_history_entry(self, ticket_id: str, action: str, moderator_id: UUID = None, comment: str = None) -> None:
        """Добавить запись в историю (заглушка)."""
        pass