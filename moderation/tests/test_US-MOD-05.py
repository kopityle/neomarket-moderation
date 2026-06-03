# app/tests/test_US-MOD-05.py
"""
US-MOD-05: жёсткая блокировка (необратимая)

Тесты для сценариев:
- hard_block_transitions_to_terminal_and_emits_event — happy path
- hard_block_event_carries_hard_block_true — флаг в событии корректный
- any_modify_on_hard_blocked_returns_403 — любые POST/PUT на карточку → 403
- edited_event_on_hard_blocked_is_ignored — событие EDITED от B2B не выводит из терминала
- deleted_event_removes_hard_blocked — событие DELETED удаляет запись
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from app.models.task import ModerationTask
from app.models.reason import BlockingReason
from app.schemas.task import TaskStatus, TaskKind
from app.models.reason import BlockingReason



class TestUSMOD05:
    """US-MOD-05: жёсткая блокировка (необратимая)"""
    
    @pytest.fixture(autouse=True)
    def cleanup(self, db_session):
        db_session.query(ModerationTask).delete()
        db_session.commit()
        yield
        db_session.query(ModerationTask).delete()
        db_session.commit()
    
    @pytest.fixture
    def soft_reason(self, db_session):
        """Мягкая причина блокировки"""
        existing = db_session.query(BlockingReason).filter(
            BlockingReason.code == "WRONG_PHOTOS"
        ).first()
        if existing:
            return existing
        
        reason = BlockingReason(
            id=str(uuid4()),
            code="WRONG_PHOTOS",
            title="Неверные фотографии",
            hard_block=False,
            is_active=True
        )
        db_session.add(reason)
        db_session.commit()
        db_session.refresh(reason)
        return reason
    
    @pytest.fixture
    def hard_reason(self, db_session):
        """Жёсткая причина блокировки"""
        existing = db_session.query(BlockingReason).filter(
            BlockingReason.code == "FORBIDDEN_GOODS"
        ).first()
        if existing:
            return existing
        
        reason = BlockingReason(
            id=str(uuid4()),
            code="FORBIDDEN_GOODS",
            title="Запрещённый товар",
            hard_block=True,
            is_active=True
        )
        db_session.add(reason)
        db_session.commit()
        db_session.refresh(reason)
        return reason
    
    def test_hard_block_transitions_to_terminal_and_emits_event(
        self, api_client, db_session, moderator_id, hard_reason
    ):
        """Happy path: жёсткая блокировка → HARD_BLOCKED"""
        seller_id = uuid4()
        
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.IN_REVIEW.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={"title": "Test", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        
        with patch('app.services.b2b_client.B2BClient.send_moderation_event', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            response = api_client.post(
                f"/api/v1/tickets/{ticket.id}/block",
                headers={"X-Moderator-Id": str(moderator_id)},
                json={
                    "blocking_reason_ids": [str(hard_reason.id)],
                    "comment": "Контрафактный товар"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == TaskStatus.HARD_BLOCKED.value
        assert data["decision_comment"] == "Контрафактный товар"
        
        db_session.refresh(ticket)
        assert ticket.status == TaskStatus.HARD_BLOCKED.value
    
    def test_hard_block_event_carries_hard_block_true(
        self, api_client, db_session, moderator_id, hard_reason
    ):
        """Событие BLOCKED + hard_block=true уходит в B2B"""
        seller_id = uuid4()
        
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.IN_REVIEW.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={"title": "Test", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        
        with patch('app.services.b2b_client.B2BClient.send_moderation_event', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            response = api_client.post(
                f"/api/v1/tickets/{ticket.id}/block",
                headers={"X-Moderator-Id": str(moderator_id)},
                json={
                    "blocking_reason_ids": [str(hard_reason.id)],
                    "comment": "Test"
                }
            )
        
        assert response.status_code == 200
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args.event_type == "BLOCKED"
        assert call_args.hard_block == True  # ← ключевая проверка!
    
    def test_modify_hard_blocked_returns_409(
        self, api_client, db_session, moderator_id, hard_reason
    ):
        """Любые попытки модификации HARD_BLOCKED тикета → 403"""
        seller_id = uuid4()
        
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.HARD_BLOCKED.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            json_after={"title": "Blocked", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Попытка одобрить
        response_approve = api_client.post(
            f"/api/v1/tickets/{ticket.id}/approve",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        assert response_approve.status_code == 409
        
        # Попытка заблокировать снова
        response_block = api_client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={
                "blocking_reason_ids": [str(hard_reason.id)],
                "comment": "Again"
            }
        )
        assert response_block.status_code == 409
        
        # Попытка вернуть в очередь
        response_release = api_client.post(
            f"/api/v1/tickets/{ticket.id}/release",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        assert response_release.status_code == 403
    
    def test_edited_event_on_hard_blocked_is_ignored(
        self, api_client, db_session, valid_service_key, moderator_id, hard_reason
    ):
        """EDITED событие от B2B игнорируется для HARD_BLOCKED тикета"""
        product_id = uuid4()
        seller_id = uuid4()
        
        # Создаём HARD_BLOCKED тикет
        ticket = ModerationTask(
            product_id=str(product_id),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.HARD_BLOCKED.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            json_after={"title": "Original", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        
        original_json = ticket.json_after
        
        # Отправляем EDITED событие
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
                    "json_before": {"title": "Original"},
                    "json_after": {"title": "New", "skus": []}
                }
            }
        )
        
        # Должен вернуть 202 (принято, но игнорируем)
        assert response.status_code == 202
        
        # Тикет остался HARD_BLOCKED, данные не изменились
        db_session.refresh(ticket)
        assert ticket.status == TaskStatus.HARD_BLOCKED.value
        assert ticket.json_after == original_json
    
    def test_deleted_event_removes_hard_blocked(
        self, api_client, db_session, valid_service_key
    ):
        """DELETED событие удаляет HARD_BLOCKED тикет из БД"""
        product_id = uuid4()
        seller_id = uuid4()
        
        ticket = ModerationTask(
            product_id=str(product_id),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.HARD_BLOCKED.value,
            queue_priority=3,
            json_after={"title": "Blocked", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        
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
        
        # Тикет удалён
        ticket_exists = db_session.query(ModerationTask).filter(
            ModerationTask.product_id == str(product_id)
        ).first()
        assert ticket_exists is None
    
    def test_hard_block_with_mixed_reasons_uses_hard_block(
        self, api_client, db_session, moderator_id, hard_reason, soft_reason
    ):
        """
        Сценарий: смешанные причины (hard + soft) → HARD_BLOCKED
        Ожидание: если хотя бы одна причина hard, итоговая блокировка жёсткая
        """
        seller_id = uuid4()
        
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.IN_REVIEW.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={"title": "Test", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        
        with patch('app.services.b2b_client.B2BClient.send_moderation_event', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            response = api_client.post(
                f"/api/v1/tickets/{ticket.id}/block",
                headers={"X-Moderator-Id": str(moderator_id)},
                json={
                    "blocking_reason_ids": [str(soft_reason.id), str(hard_reason.id)],
                    "comment": "Multiple issues including hard"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == TaskStatus.HARD_BLOCKED.value
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args.hard_block == True


# ==================== Run tests ====================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])