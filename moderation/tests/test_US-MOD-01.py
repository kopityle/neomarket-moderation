# app/tests/test_US-MOD-01.py
"""
US-MOD-01: приём событий о товаре от B2B

Тесты для сценариев:
- created_pending — событие CREATED создаёт карточку в PENDING
- edited_returns_to_review — EDITED после MODERATED/BLOCKED возвращает карточку в очередь
- edited_updates_in_review — EDITED во время IN_REVIEW обновляет поля
- deleted_archived — DELETED уводит карточку из очереди
- duplicate_event_no_side_effects — повторное событие с тем же ключом → без побочных эффектов
- missing_service_header_401 — запрос без межсервисного заголовка → 401
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.task import ModerationTask
from app.models.snapshot import ProductSnapshot, SnapshotType
from app.models.idempotency_key import IdempotencyKey
from app.schemas.task import TaskStatus, TaskKind  # ← ИСПРАВЛЕНО!


class TestUSMOD01:
    """US-MOD-01: приём событий о товаре от B2B"""
    
    # ========== HAPPY PATH ==========
    
    def test_created_pending(self, api_client, valid_service_key, product_id, seller_id, idempotency_key, db_session):
        """
        Сценарий: CREATED → создаёт карточку в PENDING
        Ожидание: тикет создан, статус PENDING, kind=CREATE, снапшот создан
        """
        response = api_client.post(
            "/api/v1/b2b/events",
            headers={"X-Service-Key": valid_service_key},
            json={
                "event_type": "PRODUCT_CREATED",
                "idempotency_key": str(idempotency_key),
                "occurred_at": datetime.utcnow().isoformat(),
                "payload": {
                    "product_id": str(product_id),
                    "seller_id": str(seller_id),
                    "queue_priority": 3,
                    "json_after": {"title": "New Product", "skus": []}
                }
            }
        )
        
        assert response.status_code == 202
        
        # Проверяем БД
        ticket = db_session.query(ModerationTask).filter(
            ModerationTask.product_id == str(product_id)
        ).first()
        
        assert ticket is not None
        assert ticket.status == TaskStatus.PENDING.value
        assert ticket.kind == TaskKind.CREATE.value
        assert ticket.seller_id == str(seller_id)
        assert ticket.queue_priority == 3
        
        # Проверяем идемпотентность
        key_record = db_session.query(IdempotencyKey).filter(
            IdempotencyKey.key == str(idempotency_key)
        ).first()
        assert key_record is not None
    
    def test_edited_returns_to_review(self, api_client, valid_service_key, db_session):
        """
        Сценарий: EDITED после MODERATED → возвращает карточку в PENDING
        Ожидание: статус сброшен в PENDING, assigned_moderator_id = None
        """
        product_id = uuid4()
        seller_id = uuid4()
        
        # Создаём APPROVED тикет
        ticket = ModerationTask(
            product_id=str(product_id),
            seller_id=str(seller_id),
            kind=TaskKind.EDIT.value,
            status=TaskStatus.APPROVED.value,
            queue_priority=3,
            json_after={"title": "Old Title", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)
        
        idempotency_key = uuid4()
        
        response = api_client.post(
            "/api/v1/b2b/events",
            headers={"X-Service-Key": valid_service_key},
            json={
                "event_type": "PRODUCT_EDITED",
                "idempotency_key": str(idempotency_key),
                "occurred_at": datetime.utcnow().isoformat(),
                "payload": {
                    "product_id": str(product_id),
                    "seller_id": str(seller_id),
                    "queue_priority": 3,
                    "json_before": {"title": "Old Title"},
                    "json_after": {"title": "New Title", "skus": []}
                }
            }
        )
        
        assert response.status_code == 202
        
        db_session.refresh(ticket)
        assert ticket.status == TaskStatus.PENDING.value
        assert ticket.assigned_moderator_id is None
        assert ticket.json_after["title"] == "New Title"
    
    def test_edited_updates_in_review(self, api_client, valid_service_key, db_session, moderator_id):
        """
        Сценарий: EDITED во время IN_REVIEW → обновляет поля и сбрасывает в PENDING
        Ожидание: статус PENDING, assigned_moderator_id = None
        """
        product_id = uuid4()
        seller_id = uuid4()
        
        # Создаём тикет в IN_REVIEW
        ticket = ModerationTask(
            product_id=str(product_id),
            seller_id=str(seller_id),
            kind=TaskKind.EDIT.value,
            status=TaskStatus.IN_REVIEW.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={"title": "Old Title", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)
        
        idempotency_key = uuid4()
        
        response = api_client.post(
            "/api/v1/b2b/events",
            headers={"X-Service-Key": valid_service_key},
            json={
                "event_type": "PRODUCT_EDITED",
                "idempotency_key": str(idempotency_key),
                "occurred_at": datetime.utcnow().isoformat(),
                "payload": {
                    "product_id": str(product_id),
                    "seller_id": str(seller_id),
                    "queue_priority": 3,
                    "json_before": {"title": "Old Title"},
                    "json_after": {"title": "New Title", "skus": []}
                }
            }
        )
        
        assert response.status_code == 202
        
        db_session.refresh(ticket)
        assert ticket.status == TaskStatus.PENDING.value
        assert ticket.assigned_moderator_id is None
        assert ticket.claimed_at is None
        assert ticket.claim_expires_at is None
        assert ticket.json_after["title"] == "New Title"
    
    def test_deleted_archived(self, api_client, valid_service_key, db_session):
        """
        Сценарий: DELETED → уводит карточку из очереди
        Ожидание: тикет удалён из БД
        """
        product_id = uuid4()
        seller_id = uuid4()
        
        # Создаём тикет
        ticket = ModerationTask(
            product_id=str(product_id),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,
            queue_priority=3,
            json_after={"title": "Test Product", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)
        
        idempotency_key = uuid4()
        
        response = api_client.post(
            "/api/v1/b2b/events",
            headers={"X-Service-Key": valid_service_key},
            json={
                "event_type": "PRODUCT_DELETED",
                "idempotency_key": str(idempotency_key),
                "occurred_at": datetime.utcnow().isoformat(),
                "payload": {
                    "product_id": str(product_id)
                }
            }
        )
        
        assert response.status_code == 202
        
        # Проверяем, что тикет удалён
        ticket_exists = db_session.query(ModerationTask).filter(
            ModerationTask.product_id == str(product_id)
        ).first()
        assert ticket_exists is None
    
    def test_edited_creates_snapshot(self, api_client, valid_service_key, db_session):
        """
        Сценарий: EDITED создаёт снапшоты BEFORE и AFTER
        Ожидание: созданы оба снапшота
        """
        product_id = uuid4()
        seller_id = uuid4()
        
        # Создаём APPROVED тикет со старым json_after
        ticket = ModerationTask(
            product_id=str(product_id),
            seller_id=str(seller_id),
            kind=TaskKind.EDIT.value,
            status=TaskStatus.APPROVED.value,
            queue_priority=3,
            json_after={"title": "Old Product", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)
        
        idempotency_key = uuid4()
        
        response = api_client.post(
            "/api/v1/b2b/events",
            headers={"X-Service-Key": valid_service_key},
            json={
                "event_type": "PRODUCT_EDITED",
                "idempotency_key": str(idempotency_key),
                "occurred_at": datetime.utcnow().isoformat(),
                "payload": {
                    "product_id": str(product_id),
                    "seller_id": str(seller_id),
                    "queue_priority": 3,
                    "json_before": {"title": "Old Product"},
                    "json_after": {"title": "New Product", "skus": []}
                }
            }
        )
        
        assert response.status_code == 202
        
        # Проверяем снапшоты
        snapshots = db_session.query(ProductSnapshot).filter(
            ProductSnapshot.task_id == ticket.id
        ).all()
        
        # Должно быть 2 снапшота (BEFORE и AFTER)
        assert len(snapshots) >= 2
        
        # snapshot_type в БД — строка, используем строки для сравнения
        before_snapshot = next((s for s in snapshots if s.snapshot_type == "BEFORE"), None)
        after_snapshot = next((s for s in snapshots if s.snapshot_type == "AFTER"), None)
        
        assert before_snapshot is not None
        assert before_snapshot.data["title"] == "Old Product"
        
        assert after_snapshot is not None
        assert after_snapshot.data["title"] == "New Product"
    
    # ========== UNHAPPY PATH ==========
    
    def test_duplicate_event_no_side_effects(self, api_client, valid_service_key, product_id, seller_id, db_session):
        """
        Сценарий: повторное событие с тем же idempotency_key → 409 Conflict
        Ожидание: второй запрос возвращает 409, дубликат не создаётся
        """
        idempotency_key = uuid4()
        
        # Первый запрос
        response1 = api_client.post(
            "/api/v1/b2b/events",
            headers={"X-Service-Key": valid_service_key},
            json={
                "event_type": "PRODUCT_CREATED",
                "idempotency_key": str(idempotency_key),
                "occurred_at": datetime.utcnow().isoformat(),
                "payload": {
                    "product_id": str(product_id),
                    "seller_id": str(seller_id),
                    "queue_priority": 3,
                    "json_after": {"title": "Test Product", "skus": []}
                }
            }
        )
        assert response1.status_code == 202
        
        # Второй запрос (дубликат)
        response2 = api_client.post(
            "/api/v1/b2b/events",
            headers={"X-Service-Key": valid_service_key},
            json={
                "event_type": "PRODUCT_CREATED",
                "idempotency_key": str(idempotency_key),
                "occurred_at": datetime.utcnow().isoformat(),
                "payload": {
                    "product_id": str(product_id),
                    "seller_id": str(seller_id),
                    "queue_priority": 3,
                    "json_after": {"title": "Test Product", "skus": []}
                }
            }
        )
        
        # Должен вернуть 409 Conflict (дубликат)
        assert response2.status_code == 409
        assert "Duplicate event" in response2.json()["detail"]
        
        # В БД должен быть только один тикет
        tickets = db_session.query(ModerationTask).filter(
            ModerationTask.product_id == str(product_id)
        ).all()
        assert len(tickets) == 1
        
        # Ключ идемпотентности должен быть один
        keys = db_session.query(IdempotencyKey).filter(
            IdempotencyKey.key == str(idempotency_key)
        ).all()
        assert len(keys) == 1
    
    def test_missing_service_header_422(self, api_client):
        """
        Сценарий: запрос без X-Service-Key → 422 Unprocessable Entity
        (по канону: required header missing)
        """
        response = api_client.post(
            "/api/v1/b2b/events",
            json={
                "event_type": "PRODUCT_CREATED",
                "idempotency_key": str(uuid4()),
                "occurred_at": datetime.utcnow().isoformat(),
                "payload": {
                    "product_id": str(uuid4()),
                    "seller_id": str(uuid4()),
                    "queue_priority": 3,
                    "json_after": {"title": "Test"}
                }
            }
        )
        
        assert response.status_code == 422  


    def test_invalid_service_header_401(self, api_client):
        """Запрос с неверным X-Service-Key → 401 Unauthorized"""
        response = api_client.post(
            "/api/v1/b2b/events",
            headers={"X-Service-Key": "wrong-key"},
            json={
                "event_type": "PRODUCT_CREATED",
                "idempotency_key": str(uuid4()),
                "occurred_at": datetime.utcnow().isoformat(),
                "payload": {
                    "product_id": str(uuid4()),
                    "seller_id": str(uuid4()),
                    "queue_priority": 3,
                    "json_after": {"title": "Test"}
                }
            }
        )
        
        assert response.status_code == 401
        assert "Invalid X-Service-Key" in response.json()["detail"]
    
    def test_hard_blocked_product_ignores_events(self, api_client, valid_service_key, db_session):
        """
        Сценарий: товар в HARD_BLOCKED игнорирует EDITED события
        Ожидание: тикет не обновляется
        """
        product_id = uuid4()
        seller_id = uuid4()
        
        # Создаём HARD_BLOCKED тикет
        ticket = ModerationTask(
            product_id=str(product_id),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.HARD_BLOCKED.value,
            queue_priority=3,
            json_after={"title": "Blocked Product", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)
        
        idempotency_key = uuid4()
        
        # Пытаемся отправить EDITED
        response = api_client.post(
            "/api/v1/b2b/events",
            headers={"X-Service-Key": valid_service_key},
            json={
                "event_type": "PRODUCT_EDITED",
                "idempotency_key": str(idempotency_key),
                "occurred_at": datetime.utcnow().isoformat(),
                "payload": {
                    "product_id": str(product_id),
                    "seller_id": str(seller_id),
                    "queue_priority": 3,
                    "json_before": {"title": "Blocked Product"},
                    "json_after": {"title": "New Product", "skus": []}
                }
            }
        )
        
        # Должен вернуть 202 (игнорируем, но не ошибка)
        assert response.status_code == 202
        
        # Тикет остался HARD_BLOCKED
        db_session.refresh(ticket)
        assert ticket.status == TaskStatus.HARD_BLOCKED.value
        assert ticket.json_after["title"] == "Blocked Product"  # не изменилось


# ==================== Run tests ====================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])