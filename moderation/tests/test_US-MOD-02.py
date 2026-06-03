# app/tests/test_US-MOD-02.py
"""
US-MOD-02: получение следующей карточки из очереди

Тесты для сценариев:
- next_returns_oldest_pending — самая старая PENDING переходит в IN_REVIEW
- concurrent_two_moderators_get_different_cards — две сессии не получают одну карточку
- empty_queue_returns_204 — пустая очередь возвращает 204
- moderator_already_has_in_review_returns_409 — попытка взять вторую карточку с активной IN_REVIEW отклоняется
"""
import pytest
import threading
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.task import ModerationTask
from app.schemas.task import TaskStatus, TaskKind  # ← ИСПРАВЛЕНО!
from app.models.snapshot import ProductSnapshot, SnapshotType
from app.models.idempotency_key import IdempotencyKey


class TestUSMOD02:
    """US-MOD-02: получение следующей карточки из очереди"""
    
    def test_next_returns_oldest_pending(self, api_client, db_session, moderator_id):
        """
        Сценарий: happy path — самая старая PENDING переходит в IN_REVIEW
        Ожидание: тикет переведён в IN_REVIEW, assigned_moderator_id проставлен,
                  claimed_at и claim_expires_at установлены
        """

        db_session.query(ModerationTask).delete()
        db_session.commit()

        # Создаём два тикета с разной датой
    
        product_id_old = uuid4()
        product_id_new = uuid4()
        seller_id = uuid4()
        
        ticket_old = ModerationTask(
            product_id=str(product_id_old),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,
            queue_priority=3,
            json_after={"title": "Old Product", "skus": []},
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        
        ticket_new = ModerationTask(
            product_id=str(product_id_new),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,
            queue_priority=3,
            json_after={"title": "New Product", "skus": []},
            created_at=datetime.utcnow(),
        )
        
        db_session.add_all([ticket_old, ticket_new])
        db_session.commit()
        
        # Берём тикет
        response = api_client.post(
            "/api/v1/queue/claim",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["product_id"] == str(product_id_old)  # самый старый
        assert data["status"] == TaskStatus.IN_REVIEW.value
        assert data["assigned_moderator_id"] == str(moderator_id)
        assert data["claimed_at"] is not None
        assert data["claim_expires_at"] is not None
        
        # Проверяем БД
        db_session.refresh(ticket_old)
        assert ticket_old.status == TaskStatus.IN_REVIEW.value
        assert ticket_old.assigned_moderator_id == str(moderator_id)
    
    def test_next_with_priority_filter(self, api_client, db_session, moderator_id):
        """
        Сценарий: фильтрация по queue_priority
        Ожидание: берётся тикет из указанной очереди
        """
        db_session.query(ModerationTask).delete()
        db_session.commit()
        seller_id = uuid4()
        
        # Тикет с приоритетом 1 (высокий)
        ticket_high = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,
            queue_priority=1,
            json_after={"title": "High Priority", "skus": []},
        )
        
        # Тикет с приоритетом 3 (обычный)
        ticket_normal = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,
            queue_priority=3,
            json_after={"title": "Normal Priority", "skus": []},
        )
        
        db_session.add_all([ticket_high, ticket_normal])
        db_session.commit()
        
        # Запрашиваем только очередь с приоритетом 3
        response = api_client.post(
            "/api/v1/queue/claim",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={"queue_priority": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["product_id"] == str(ticket_normal.product_id)
        assert data["queue_priority"] == 3
    
    def test_concurrent_two_moderators_get_different_cards(self, api_client, db_session):
        """
        Сценарий: два модератора последовательно запрашивают карточки через API
        """
        # Очищаем БД перед тестом
        db_session.query(ModerationTask).delete()
        db_session.commit()
        
        seller_id = uuid4()
        moderator_1 = uuid4()
        moderator_2 = uuid4()
        
        # Создаём два тикета
        for i in range(2):
            ticket = ModerationTask(
                product_id=str(uuid4()),
                seller_id=str(seller_id),
                kind=TaskKind.CREATE.value,
                status=TaskStatus.PENDING.value,
                queue_priority=3,
                json_after={"title": f"Ticket {i+1}", "skus": []},
            )
            db_session.add(ticket)
        db_session.commit()
        
        # Первый модератор берёт тикет
        response1 = api_client.post(
            "/api/v1/queue/claim",
            headers={"X-Moderator-Id": str(moderator_1)},
            json={}
        )
        assert response1.status_code == 200, f"Expected 200, got {response1.status_code}"
        ticket1_id = response1.json()["id"]
        
        # Второй модератор берёт тикет
        response2 = api_client.post(
            "/api/v1/queue/claim",
            headers={"X-Moderator-Id": str(moderator_2)},
            json={}
        )
        assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
        ticket2_id = response2.json()["id"]
        
        # Тикеты должны быть разными
        assert ticket1_id != ticket2_id
    
    def test_empty_queue_returns_204(self, api_client, db_session, moderator_id):
        """
        Сценарий: пустая очередь → 204 No Content
        Ожидание: 204 без тела
        """
        db_session.query(ModerationTask).delete()
        db_session.commit()
        response = api_client.post(
            "/api/v1/queue/claim",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        
        assert response.status_code == 204
    
    def test_moderator_already_has_in_review_returns_409(self, api_client, db_session, moderator_id):
        """
        Сценарий: у модератора уже есть IN_REVIEW тикет → 409 Conflict
        Ожидание: 409, второй тикет не выдан
        """
        seller_id = uuid4()
        
        # Создаём IN_REVIEW тикет для модератора
        active_ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.IN_REVIEW.value,
            assigned_moderator_id=str(moderator_id),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={"title": "Active Ticket", "skus": []},
        )
        
        # Создаём PENDING тикет
        pending_ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,
            queue_priority=3,
            json_after={"title": "Pending Ticket", "skus": []},
        )
        
        db_session.add_all([active_ticket, pending_ticket])
        db_session.commit()
        
        # Пытаемся взять второй тикет
        response = api_client.post(
            "/api/v1/queue/claim",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        
        assert response.status_code == 409
        assert "You already have an active review ticket" in response.json()["detail"]
        
        # Проверяем, что второй тикет не изменился
        db_session.refresh(pending_ticket)
        assert pending_ticket.status == TaskStatus.PENDING.value
    
    def test_claim_with_category_filter(self, api_client, db_session, moderator_id):
        """
        Сценарий: фильтрация по category_ids
        Ожидание: берётся тикет из указанной категории
        """
        seller_id = uuid4()
        category_1 = uuid4()
        category_2 = uuid4()
        
        ticket_category_1 = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,
            queue_priority=3,
            category_id=str(category_1),
            json_after={"title": "Category 1", "skus": []},
        )
        
        ticket_category_2 = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,
            queue_priority=3,
            category_id=str(category_2),
            json_after={"title": "Category 2", "skus": []},
        )
        
        db_session.add_all([ticket_category_1, ticket_category_2])
        db_session.commit()
        
        # Запрашиваем только категорию 1
        response = api_client.post(
            "/api/v1/queue/claim",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={"category_ids": [str(category_1)]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == str(ticket_category_1.product_id)
    
    def test_claim_auto_priority_order(self, api_client, db_session, moderator_id):
        """
        Сценарий: автоприоритизация — берётся тикет из наименьшей очереди (1)
        Ожидание: даже если есть очередь 3, сначала возьмётся очередь 1
        """
        seller_id = uuid4()
        
        # Тикет с приоритетом 3 (обычный)
        ticket_normal = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,
            queue_priority=3,
            json_after={"title": "Normal", "skus": []},
        )
        
        # Тикет с приоритетом 1 (высокий)
        ticket_high = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,
            queue_priority=1,
            json_after={"title": "High", "skus": []},
        )
        
        db_session.add_all([ticket_normal, ticket_high])
        db_session.commit()
        
        # Берём тикет без указания приоритета (авто)
        response = api_client.post(
            "/api/v1/queue/claim",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Должен вернуть тикет с приоритетом 1
        assert data["queue_priority"] == 1
        assert data["product_id"] == str(ticket_high.product_id)
    
    def test_claim_with_expired_in_review_not_blocking(self, api_client, db_session, moderator_id):
        """
        Сценарий: у модератора был IN_REVIEW, но истёк TTL
        Ожидание: модератор может взять новый тикет
        """
        # Очищаем БД перед тестом
        db_session.query(ModerationTask).delete()
        db_session.commit()
        
        seller_id = uuid4()
        
        # Создаём просроченный IN_REVIEW тикет
        expired_ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.IN_REVIEW.value,
            assigned_moderator_id=str(moderator_id),
            claimed_at=datetime.utcnow() - timedelta(minutes=31),
            claim_expires_at=datetime.utcnow() - timedelta(minutes=1),
            json_after={"title": "Expired", "skus": []},
        )
        
        # Создаём PENDING тикет
        pending_ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,
            queue_priority=3,
            json_after={"title": "Pending", "skus": []},
        )
        
        db_session.add_all([expired_ticket, pending_ticket])
        db_session.commit()
        
        # Берём новый тикет
        response = api_client.post(
            "/api/v1/queue/claim",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Должен вернуть PENDING тикет (просроченный не блокирует)
        # Но может вернуть просроченный, так как он IN_REVIEW?
        # Проверяем, что вернулся не просроченный
        assert data["product_id"] == str(pending_ticket.product_id)


# ==================== Run tests ====================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])