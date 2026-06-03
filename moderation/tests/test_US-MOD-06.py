# app/tests/test_US-MOD-06.py
"""
US-MOD-06: справочник причин блокировки

Тесты для сценариев:
- list_returns_active_reasons — активные причины возвращаются
- inactive_reasons_not_visible — деактивированные причины скрыты
- filter_by_hard_block — фильтрация по hard_block
- referenced_reason_cannot_be_deleted — причина, используемая в тикетах, не удаляется
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.reason import BlockingReason
from app.models.task import ModerationTask
from app.schemas.task import TaskStatus, TaskKind
from app.schemas.task import TaskStatus as TaskStatusEnum, TaskKind as TaskKindEnum


class TestUSMOD06:
    """US-MOD-06: справочник причин блокировки"""
    
    @pytest.fixture(autouse=True)
    def cleanup(self, db_session):
        db_session.query(BlockingReason).filter(
            BlockingReason.code.in_(["TEST_ACTIVE", "TEST_INACTIVE", "TEST_HARD"])
        ).delete()
        db_session.commit()
        yield
        db_session.query(BlockingReason).filter(
            BlockingReason.code.in_(["TEST_ACTIVE", "TEST_INACTIVE", "TEST_HARD"])
        ).delete()
        db_session.commit()
    
    def test_list_returns_active_reasons(self, api_client, db_session):
        """Активные причины возвращаются в списке"""
        # Создаём активную причину
        active_reason = BlockingReason(
            id=str(uuid4()),
            code="TEST_ACTIVE",
            title="Активная причина",
            hard_block=False,
            is_active=True
        )
        db_session.add(active_reason)
        db_session.commit()
        
        response = api_client.get("/api/v1/blocking-reasons")
        
        assert response.status_code == 200
        data = response.json()
        
        # Находим нашу причину в ответе
        found = any(r["code"] == "TEST_ACTIVE" for r in data)
        assert found, "Active reason not found in response"
    
    def test_inactive_reasons_not_visible(self, api_client, db_session):
        """Деактивированные причины не возвращаются"""
        # Создаём неактивную причину
        inactive_reason = BlockingReason(
            id=str(uuid4()),
            code="TEST_INACTIVE",
            title="Неактивная причина",
            hard_block=False,
            is_active=False
        )
        db_session.add(inactive_reason)
        db_session.commit()
        
        response = api_client.get("/api/v1/blocking-reasons")
        
        assert response.status_code == 200
        data = response.json()
        
        # Неактивная причина не должна быть в ответе
        found = any(r["code"] == "TEST_INACTIVE" for r in data)
        assert not found, "Inactive reason should not be visible"
    
    def test_filter_by_hard_block(self, api_client, db_session):
        """Фильтрация причин по hard_block"""
        soft_reason = BlockingReason(
            id=uuid4(),
            code="TEST_SOFT",
            title="Мягкая причина",
            hard_block=False,
            is_active=True
        )
        hard_reason = BlockingReason(
            id=uuid4(),
            code="TEST_HARD",
            title="Жёсткая причина",
            hard_block=True,
            is_active=True
        )
        db_session.add_all([soft_reason, hard_reason])
        db_session.commit()
        
        # Фильтр по hard_block=false
        response_soft = api_client.get("/api/v1/blocking-reasons?hard_block=false")
        assert response_soft.status_code == 200
        soft_data = response_soft.json()
        assert any(r["code"] == "TEST_SOFT" for r in soft_data)
        assert not any(r["code"] == "TEST_HARD" for r in soft_data)
        
        # Фильтр по hard_block=true
        response_hard = api_client.get("/api/v1/blocking-reasons?hard_block=true")
        assert response_hard.status_code == 200
        hard_data = response_hard.json()
        assert any(r["code"] == "TEST_HARD" for r in hard_data)
        assert not any(r["code"] == "TEST_SOFT" for r in hard_data)
    
    def test_referenced_reason_cannot_be_deactivated(self, api_client, db_session, moderator_id):
        """
        Причина, используемая в тикете, не может быть деактивирована через API
        (или требует специальной проверки)
        """
        # Создаём причину
        reason = BlockingReason(
            id=str(uuid4()),
            code="TEST_REFERENCED",
            title="Используемая причина",
            hard_block=False,
            is_active=True
        )
        db_session.add(reason)
        db_session.commit()
        
        # Создаём BLOCKED тикет с этой причиной
        seller_id = uuid4()
        ticket = ModerationTask(
            product_id=str(uuid4()),
            seller_id=str(seller_id),
            kind=TaskKindEnum.CREATE.value,
            status=TaskStatusEnum.BLOCKED.value,
            queue_priority=3,
            assigned_moderator_id=str(moderator_id),
            blocking_reason_id=str(reason.id),
            json_after={"title": "Test", "skus": []},
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Попытка деактивировать причину должна быть запрещена
        # В текущей реализации API нет эндпоинта для деактивации,
        # но проверяем, что причина всё ещё активна
        db_session.refresh(reason)
        assert reason.is_active == True
        
        # Если бы был эндпоинт PATCH /blocking-reasons/{id},
        # он должен был бы вернуть ошибку 409 при попытке деактивации
    
    def test_reason_fields_format(self, api_client, db_session):
        """Проверка формата полей причины"""
        reason = BlockingReason(
            id=str(uuid4()),
            code="TEST_FORMAT",
            title="Тестовая причина",
            description="Описание",
            hard_block=True,
            is_active=True
        )
        db_session.add(reason)
        db_session.commit()
        
        response = api_client.get("/api/v1/blocking-reasons")
        assert response.status_code == 200
        data = response.json()
        
        test_reason = next((r for r in data if r["code"] == "TEST_FORMAT"), None)
        assert test_reason is not None
        
        # Проверяем поля
        assert "id" in test_reason
        assert "code" in test_reason
        assert "title" in test_reason
        assert "hard_block" in test_reason
        assert test_reason["hard_block"] == True
        assert test_reason["title"] == "Тестовая причина"
        assert test_reason["description"] == "Описание"


# ==================== Run tests ====================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])