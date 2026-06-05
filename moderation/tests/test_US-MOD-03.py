# app/tests/test_US-MOD-03.py
"""
US-MOD-03: одобрение товара модератором

Тесты для сценариев:
- approve_transitions_to_moderated_and_emits_event — happy path
- approve_others_card_returns_403 — модератор не может одобрить чужую карточку
- approve_after_edited_returns_409 — товар изменён во время ревью
- approve_without_sku_returns_409 — товар без SKU нельзя одобрить
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from app.models.task import ModerationTask
from app.schemas.task import TaskStatus, TaskKind  # ← ИСПРАВЛЕНО!
from app.schemas.b2b import ModerationEventRequest, ModerationEventType


class TestUSMOD03:
    """US-MOD-03: одобрение товара модератором"""
    
    @pytest.fixture(autouse=True)
    def cleanup(self, db_session):
        """Очистка БД перед каждым тестом"""
        db_session.query(ModerationTask).delete()
        db_session.commit()
        yield
        db_session.query(ModerationTask).delete()
        db_session.commit()
    
    def test_approve_transitions_to_moderated_and_emits_event(
        self, api_client, db_session, moderator_id
    ):
        """
        Сценарий: happy path — одобрение товара
        Ожидание: статус → MODERATED, событие MODERATED в B2B уходит
        """
        seller_id = uuid4()
        product_id = uuid4()
        
        # Создаём IN_REVIEW тикет
        ticket = ModerationTask(
            product_id=str(product_id),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.IN_REVIEW.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={
                "title": "Test Product",
                "skus": [{"id": str(uuid4()), "name": "SKU 1"}]
            },
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Мокаем отправку события в B2B
        with patch('app.services.b2b_client.B2BClient.send_moderation_event', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            response = api_client.post(
                f"/api/v1/tickets/{ticket.id}/approve",
                headers={"X-Moderator-Id": str(moderator_id)},
                json={"comment": "Good product"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == TaskStatus.APPROVED.value
        assert data.get("decision_comment") == "Good product"
        assert data.get("decision_at") is not None
        
        # Проверяем БД
        db_session.refresh(ticket)
        assert ticket.status == TaskStatus.APPROVED.value
        assert ticket.decision_comment == "Good product"
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args.event_type == ModerationEventType.MODERATED
        assert call_args.hard_block == False
        assert call_args.blocking_reason_id is None
    
    def test_approve_others_card_returns_409(self, api_client, db_session):
        """Модератор пытается одобрить чужую карточку → 409 Conflict"""
        seller_id = uuid4()
        moderator_1 = uuid4()
        moderator_2 = uuid4()
        
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.IN_REVIEW.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_1),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={"title": "Test", "skus": [{"id": str(uuid4())}]},
        )
        db_session.add(ticket)
        db_session.commit()
        
        response = api_client.post(
            f"/api/v1/tickets/{ticket.id}/approve",
            headers={"X-Moderator-Id": str(moderator_2)},
            json={}
        )
        
        assert response.status_code == 409  # ← по канону 409
    
    def test_approve_after_edited_returns_409(self, api_client, db_session, moderator_id):
        """
        Сценарий: продавец отредактировал товар во время ревью
        Ожидание: 409 Conflict
        """
        seller_id = uuid4()
        
        # Создаём IN_REVIEW тикет
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.IN_REVIEW.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={"title": "Original", "skus": [{"id": str(uuid4())}]},
        )
        db_session.add(ticket)
        
        # Симулируем обновление товара (EDITED) — увеличиваем updated_at
        ticket.updated_at = datetime.utcnow() + timedelta(seconds=10)
        db_session.commit()
        
        response = api_client.post(
            f"/api/v1/tickets/{ticket.id}/approve",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        
        assert response.status_code == 409
        assert "edited" in response.json()["detail"].lower() or "changed" in response.json()["detail"].lower()
    
    def test_approve_without_sku_returns_409(self, api_client, db_session, moderator_id):
        """
        Сценарий: товар без SKU нельзя одобрить
        Ожидание: 409 Conflict
        """
        seller_id = uuid4()
        
        # Создаём IN_REVIEW тикет без SKU
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.IN_REVIEW.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={"title": "Test Product", "skus": []},  # ← пустые SKU
        )
        db_session.add(ticket)
        db_session.commit()
        
        response = api_client.post(
            f"/api/v1/tickets/{ticket.id}/approve",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        
        assert response.status_code == 409
        assert "SKU" in response.json()["detail"] or "skus" in response.json()["detail"].lower()
    
    def test_approve_hard_blocked_returns_409(self, api_client, db_session, moderator_id):
        """
        Сценарий: попытка одобрить HARD_BLOCKED тикет
        Ожидание: 409 Conflict
        """
        seller_id = uuid4()
        
        # Создаём HARD_BLOCKED тикет
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.HARD_BLOCKED.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            json_after={"title": "Blocked", "skus": [{"id": str(uuid4())}]},
        )
        db_session.add(ticket)
        db_session.commit()
        
        response = api_client.post(
            f"/api/v1/tickets/{ticket.id}/approve",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        
        assert response.status_code == 409
        assert "HARD_BLOCKED" in response.json()["detail"] or "cannot approve" in response.json()["detail"].lower()
    
    def test_approve_non_existent_ticket_returns_404(self, api_client, moderator_id):
        """
        Сценарий: тикет не существует
        Ожидание: 404 Not Found
        """
        fake_id = uuid4()
        
        response = api_client.post(
            f"/api/v1/tickets/{fake_id}/approve",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        
        assert response.status_code == 404
    
    def test_approve_pending_ticket_returns_409(self, api_client, db_session, moderator_id):
        """
        Сценарий: попытка одобрить PENDING тикет (не взятый в работу)
        Ожидание: 409 Conflict
        """
        seller_id = uuid4()
        
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKind.CREATE.value,
            status=TaskStatus.PENDING.value,  # ← PENDING, не IN_REVIEW
            queue_priority=3,
            assigned_moderator_id=None,
            json_after={"title": "Pending", "skus": [{"id": str(uuid4())}]},
        )
        db_session.add(ticket)
        db_session.commit()
        
        response = api_client.post(
            f"/api/v1/tickets/{ticket.id}/approve",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={}
        )
        
        assert response.status_code == 409
        
        # Проверяем, что сообщение говорит о неверном статусе
        detail = response.json()["detail"].lower()
        assert "pending" in detail or "not in review" in detail 


# ==================== Run tests ====================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])