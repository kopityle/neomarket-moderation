# app/tests/test_US-MOD-04.py
"""
US-MOD-04: мягкая блокировка с замечаниями

Тесты для сценариев:
- soft_block_transitions_to_blocked_with_field_reports — happy path
- soft_block_emits_event_to_b2b — событие BLOCKED + hard_block=false уходит в B2B
- soft_block_unknown_reason_returns_400 — несуществующий blocking_reason_id → 400
- soft_block_others_card_returns_409 — чужая карточка → 409
- soft_block_invalid_field_name_returns_400 — поле field_reports[].field_path вне допустимого enum → 400
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from app.models.task import ModerationTask
from app.schemas.task import TaskStatus, TaskKind
from app.models.reason import BlockingReason
from app.schemas.task import TaskStatus as TaskStatusEnum, TaskKind as TaskKindEnum


class TestUSMOD04:
    """US-MOD-04: мягкая блокировка с замечаниями"""
    
    @pytest.fixture(autouse=True)
    def cleanup(self, db_session):
        db_session.query(ModerationTask).delete()
        db_session.commit()
        yield
        db_session.query(ModerationTask).delete()
        db_session.commit()
    
    @pytest.fixture
    def soft_reason(self, db_session):
        """Мягкая причина блокировки (создаём только если нет)"""
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
        """Жёсткая причина блокировки (создаём только если нет)"""
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
    
    def test_soft_block_transitions_to_blocked_with_field_reports(
    self, api_client, db_session, moderator_id, soft_reason
):
        """Happy path: мягкая блокировка с замечаниями"""
        seller_id = uuid4()
        
        ticket = ModerationTask(
            product_id=uuid4(),
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
        
        # Добавим отладочный вывод
        print(f"\nTicket ID: {ticket.id}")
        print(f"Moderator ID: {moderator_id}")
        print(f"Reason ID: {soft_reason.id}")
        
        with patch('app.services.b2b_client.B2BClient.send_moderation_event', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            response = api_client.post(
                f"/api/v1/tickets/{ticket.id}/block",
                headers={"X-Moderator-Id": str(moderator_id)},
                json={
                    "blocking_reason_ids": [str(soft_reason.id)],
                    "comment": "Фото не соответствуют товару",
                    "field_reports": [
                        {
                            "field_path": "images[0].url",
                            "message": "Фото размытое",
                            "severity": "ERROR"
                        },
                        {
                            "field_path": "description",
                            "message": "Описание скопировано",
                            "severity": "WARNING"
                        }
                    ]
                }
            )
            
            # Добавим отладочный вывод
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json() if response.status_code != 204 else 'No content'}")
        
        assert response.status_code == 200
        # ... остальные проверки
        data = response.json()
        
        assert data["status"] == TaskStatusEnum.BLOCKED.value
        assert data["decision_comment"] == "Фото не соответствуют товару"
        
        db_session.refresh(ticket)
        assert ticket.status == TaskStatusEnum.BLOCKED.value
        assert ticket.decision_comment == "Фото не соответствуют товару"
    
    def test_soft_block_emits_event_to_b2b(
        self, api_client, db_session, moderator_id, soft_reason
    ):
        """Проверка отправки события BLOCKED + hard_block=false в B2B"""
        seller_id = uuid4()
        
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKindEnum.CREATE.value,
            status=TaskStatusEnum.IN_REVIEW.value,
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
                    "blocking_reason_ids": [str(soft_reason.id)],
                    "comment": "Test comment"
                }
            )
        
        assert response.status_code == 200
        
        # Проверяем, что событие было отправлено с правильными параметрами
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args.event_type == "BLOCKED"
        assert call_args.hard_block == False
        assert call_args.moderator_comment == "Test comment"
    
    def test_soft_block_unknown_reason_returns_400(
        self, api_client, db_session, moderator_id
    ):
        """Несуществующий blocking_reason_id → 400"""
        seller_id = uuid4()
        fake_reason_id = uuid4()
        
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKindEnum.CREATE.value,
            status=TaskStatusEnum.IN_REVIEW.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={"title": "Test", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        
        response = api_client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={
                "blocking_reason_ids": [str(fake_reason_id)],
                "comment": "Test"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"] or "reason" in response.json()["detail"].lower()
    
    def test_soft_block_others_card_returns_409(
        self, api_client, db_session, soft_reason
    ):
        """Чужая карточка → 409 Conflict"""
        seller_id = uuid4()
        moderator_1 = uuid4()
        moderator_2 = uuid4()
        
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKindEnum.CREATE.value,
            status=TaskStatusEnum.IN_REVIEW.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_1),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={"title": "Test", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        
        response = api_client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            headers={"X-Moderator-Id": str(moderator_2)},
            json={
                "blocking_reason_ids": [str(soft_reason.id)],
                "comment": "Test"
            }
        )
        
        assert response.status_code == 409
        assert "not assigned" in response.json()["detail"].lower()
    
    def test_soft_block_invalid_field_name_returns_400(
        self, api_client, db_session, moderator_id, soft_reason
    ):
        """Поле field_reports[].field_path вне допустимого enum → 400"""
        seller_id = uuid4()
        
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKindEnum.CREATE.value,
            status=TaskStatusEnum.IN_REVIEW.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            claimed_at=datetime.utcnow(),
            claim_expires_at=datetime.utcnow() + timedelta(minutes=30),
            json_after={"title": "Test", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        
        response = api_client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={
                "blocking_reason_ids": [str(soft_reason.id)],
                "comment": "Test",
                "field_reports": [
                    {
                        "field_path": "invalid_field_name",
                        "message": "This field is not allowed",
                        "severity": "ERROR"
                    }
                ]
            }
        )
        
        assert response.status_code == 400
        assert "field" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()
    
    def test_soft_block_pending_ticket_returns_409(
        self, api_client, db_session, moderator_id, soft_reason
    ):
        """PENDING тикет (не взят в работу) → 409"""
        seller_id = uuid4()
        
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKindEnum.CREATE.value,
            status=TaskStatusEnum.PENDING.value,
            queue_priority=3,
            assigned_moderator_id=None,
            json_after={"title": "Test", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        
        response = api_client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={
                "blocking_reason_ids": [str(soft_reason.id)],
                "comment": "Test"
            }
        )
        
        assert response.status_code == 409
        assert "status" in response.json()["detail"].lower()
    
    def test_soft_block_with_multiple_reasons(
        self, api_client, db_session, moderator_id, soft_reason
    ):
        """Несколько мягких причин → всё ещё мягкая блокировка"""
        # Получаем или создаём вторую причину
        reason2 = db_session.query(BlockingReason).filter(
            BlockingReason.code == "INCORRECT_CATEGORY"
        ).first()
        
        if not reason2:
            reason2 = BlockingReason(
                id=str(uuid4()),
                code="INCORRECT_CATEGORY",
                title="Неверная категория",
                hard_block=False,
                is_active=True
            )
            db_session.add(reason2)
            db_session.commit()
            db_session.refresh(reason2)
        
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
        
        response = api_client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            headers={"X-Moderator-Id": str(moderator_id)},
            json={
                "blocking_reason_ids": [str(soft_reason.id), str(reason2.id)],
                "comment": "Multiple issues"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == TaskStatus.BLOCKED.value


# ==================== Run tests ====================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])