"""
US-MOD-07: CRUD операции с причинами блокировки (ADMIN)

Тесты для сценариев:
- create_blocking_reason_success — создание новой причины
- create_blocking_reason_duplicate_code — 409 при дубликате кода
- create_blocking_reason_requires_admin — 403 для не-ADMIN
- update_blocking_reason_success — обновление причины
- update_blocking_reason_not_found — 404 при обновлении несуществующей
- update_blocking_reason_requires_admin — 403 для не-ADMIN
- deactivate_blocking_reason_success — деактивация причины
- deactivate_blocking_reason_not_found — 404 при деактивации несуществующей
- deactivate_blocking_reason_requires_admin — 403 для не-ADMIN
- get_blocking_reason_by_id — получение одной причины
"""
import pytest
from uuid import uuid4
from datetime import datetime

from app.models.reason import BlockingReason
from app.models.moderator import Moderator, ModeratorRole
from app.schemas.task import TaskStatus, TaskKind
from app.models.reason import BlockingReason as BlockingReasonModel  # ← модель SQLAlchemy
from app.schemas.reason import BlockingReasonResponse, BlockingReasonCreate, BlockingReasonUpdate


class TestUSMOD07:
    """US-MOD-07: CRUD операции с причинами блокировки (только ADMIN)"""
    
    @pytest.fixture
    def admin_moderator_id(self, db_session):
        """Создать ADMIN модератора для тестов"""
        moderator_id = uuid4()
        moderator = Moderator(
            id=moderator_id,
            email=f"admin_{uuid4()}@test.com",
            password_hash="fake_hash",
            first_name="Admin",
            role=ModeratorRole.ADMIN,
            is_active=True,
        )
        db_session.add(moderator)
        db_session.commit()
        return moderator_id
    
    @pytest.fixture
    def regular_moderator_id(self, db_session):
        """Создать обычного модератора для тестов"""
        moderator_id = uuid4()
        moderator = Moderator(
            id=moderator_id,
            email=f"moderator_{uuid4()}@test.com",
            password_hash="fake_hash",
            first_name="Moderator",
            role=ModeratorRole.MODERATOR,
            is_active=True,
        )
        db_session.add(moderator)
        db_session.commit()
        return moderator_id
    
    @pytest.fixture
    def test_reason(self, db_session):
        """Создать тестовую причину"""
        reason = BlockingReason(
            id=str(uuid4()),
            code="TEST_CRUD_REASON",
            title="Test CRUD Reason",
            description="Original description",
            hard_block=False,
            is_active=True,
        )
        db_session.add(reason)
        db_session.commit()
        db_session.refresh(reason)
        return reason
    
    def cleanup(self, db_session):
        """Очистка тестовых данных"""
        db_session.query(BlockingReason).filter(
            BlockingReason.code.like("TEST_%")
        ).delete()
        db_session.commit()
    
    # ==================== CREATE ====================
    
    def test_create_blocking_reason_success(self, api_client, db_session, admin_moderator_id):
        """Создание новой причины блокировки (ADMIN)"""
        self.cleanup(db_session)
        
        response = api_client.post(
            "/api/v1/blocking-reasons",
            headers={"X-Moderator-Id": str(admin_moderator_id)},
            json={
                "code": "TEST_NEW_REASON",
                "title": "Новая причина",
                "description": "Описание новой причины",
                "hard_block": False,
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["code"] == "TEST_NEW_REASON"
        assert data["title"] == "Новая причина"
        assert data["description"] == "Описание новой причины"
        assert data["hard_block"] == False
        assert data["is_active"] == True
        assert "id" in data
        
        # Проверяем БД
        reason = db_session.query(BlockingReason).filter(
            BlockingReason.code == "TEST_NEW_REASON"
        ).first()
        assert reason is not None
        assert reason.title == "Новая причина"
    
    def test_create_blocking_reason_duplicate_code(self, api_client, db_session, admin_moderator_id, test_reason):
        """409 Conflict при создании причины с существующим кодом"""
        response = api_client.post(
            "/api/v1/blocking-reasons",
            headers={"X-Moderator-Id": str(admin_moderator_id)},
            json={
                "code": "TEST_CRUD_REASON",  # тот же код, что в test_reason
                "title": "Другая причина",
                "description": "Описание",
                "hard_block": False,
            }
        )
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    
    def test_create_blocking_reason_requires_admin(self, api_client, db_session, regular_moderator_id):
        """403 Forbidden при создании причины обычным модератором"""
        response = api_client.post(
            "/api/v1/blocking-reasons",
            headers={"X-Moderator-Id": str(regular_moderator_id)},
            json={
                "code": "TEST_NO_ADMIN",
                "title": "Нет прав",
                "description": "Описание",
                "hard_block": False,
            }
        )
        
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]
    
    def test_create_blocking_reason_invalid_code_format(self, api_client, db_session, admin_moderator_id):
        """400 Bad Request при неверном формате кода (только заглавные буквы и подчёркивания)"""
        response = api_client.post(
            "/api/v1/blocking-reasons",
            headers={"X-Moderator-Id": str(admin_moderator_id)},
            json={
                "code": "invalid-code",  # lowercase и дефис
                "title": "Неверный код",
                "description": "Описание",
                "hard_block": False,
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    # ==================== UPDATE ====================
    
    def test_update_blocking_reason_success(self, api_client, db_session, admin_moderator_id, test_reason):
        """Обновление причины блокировки (ADMIN)"""
        response = api_client.patch(
            f"/api/v1/blocking-reasons/{test_reason.id}",
            headers={"X-Moderator-Id": str(admin_moderator_id)},
            json={
                "title": "Обновлённое название",
                "description": "Новое описание",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["title"] == "Обновлённое название"
        assert data["description"] == "Новое описание"
        assert data["code"] == "TEST_CRUD_REASON"  # код не изменился
        assert data["hard_block"] == False  # hard_block не изменился
        
        # Проверяем БД
        db_session.refresh(test_reason)
        assert test_reason.title == "Обновлённое название"
        assert test_reason.description == "Новое описание"
    
    def test_update_blocking_reason_not_found(self, api_client, db_session, admin_moderator_id):
        """404 Not Found при обновлении несуществующей причины"""
        fake_id = uuid4()
        response = api_client.patch(
            f"/api/v1/blocking-reasons/{fake_id}",
            headers={"X-Moderator-Id": str(admin_moderator_id)},
            json={"title": "Новое название"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_update_blocking_reason_requires_admin(self, api_client, db_session, regular_moderator_id, test_reason):
        """403 Forbidden при обновлении причины обычным модератором"""
        response = api_client.patch(
            f"/api/v1/blocking-reasons/{test_reason.id}",
            headers={"X-Moderator-Id": str(regular_moderator_id)},
            json={"title": "Попытка изменения"}
        )
        
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]
    
    def test_update_blocking_reason_cannot_change_hard_block(self, api_client, db_session, admin_moderator_id, test_reason):
        """hard_block не должен меняться при обновлении (по канону OpenAPI)"""
        original_hard_block = test_reason.hard_block
        
        response = api_client.patch(
            f"/api/v1/blocking-reasons/{test_reason.id}",
            headers={"X-Moderator-Id": str(admin_moderator_id)},
            json={
                "title": "Новое название",
                "hard_block": True,  # пытаемся изменить
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # hard_block не должен измениться
        assert data["hard_block"] == original_hard_block
        
        db_session.refresh(test_reason)
        assert test_reason.hard_block == original_hard_block
    
    # ==================== DELETE (DEACTIVATE) ====================
    
    def test_deactivate_blocking_reason_success(self, api_client, db_session, admin_moderator_id, test_reason):
        """Деактивация причины блокировки (ADMIN)"""
        assert test_reason.is_active == True
        
        response = api_client.delete(
            f"/api/v1/blocking-reasons/{test_reason.id}",
            headers={"X-Moderator-Id": str(admin_moderator_id)},
        )
        
        assert response.status_code == 204
        assert response.text == "" or response.content == b""
        
        # Проверяем БД
        db_session.refresh(test_reason)
        assert test_reason.is_active == False
    
    def test_deactivate_blocking_reason_not_found(self, api_client, db_session, admin_moderator_id):
        """404 Not Found при деактивации несуществующей причины"""
        fake_id = uuid4()
        response = api_client.delete(
            f"/api/v1/blocking-reasons/{fake_id}",
            headers={"X-Moderator-Id": str(admin_moderator_id)},
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_deactivate_blocking_reason_requires_admin(self, api_client, db_session, regular_moderator_id, test_reason):
        """403 Forbidden при деактивации причины обычным модератором"""
        response = api_client.delete(
            f"/api/v1/blocking-reasons/{test_reason.id}",
            headers={"X-Moderator-Id": str(regular_moderator_id)},
        )
        
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]
    
    def test_deactivated_reason_not_in_list(self, api_client, db_session, admin_moderator_id, test_reason):
        """Деактивированная причина не отображается в списке (GET /blocking-reasons)"""
        # Деактивируем причину
        response = api_client.delete(
            f"/api/v1/blocking-reasons/{test_reason.id}",
            headers={"X-Moderator-Id": str(admin_moderator_id)},
        )
        assert response.status_code == 204
        
        # Проверяем, что её нет в списке
        response = api_client.get("/api/v1/blocking-reasons")
        assert response.status_code == 200
        data = response.json()
        
        found = any(r["code"] == "TEST_CRUD_REASON" for r in data)
        assert not found, "Deactivated reason should not be in list"
    
    def test_deactivated_reason_visible_with_is_active_false(self, api_client, db_session, admin_moderator_id, test_reason):
        """Деактивированная причина видна при is_active=false"""
        # Деактивируем причину
        response = api_client.delete(
            f"/api/v1/blocking-reasons/{test_reason.id}",
            headers={"X-Moderator-Id": str(admin_moderator_id)},
        )
        assert response.status_code == 204
        
        # Запрашиваем с is_active=false
        response = api_client.get("/api/v1/blocking-reasons?is_active=false")
        assert response.status_code == 200
        data = response.json()
        
        found = any(r["code"] == "TEST_CRUD_REASON" for r in data)
        assert found, "Deactivated reason should be visible when is_active=false"
    
    # ==================== GET BY ID (если есть эндпоинт) ====================
    
    def test_get_blocking_reason_by_id(self, api_client, db_session, admin_moderator_id, test_reason):
        """Получение одной причины по ID (если эндпоинт есть)"""
        # В текущей реализации нет GET /blocking-reasons/{id},
        # но если добавите, вот тест:
        response = api_client.get(
            f"/api/v1/blocking-reasons/{test_reason.id}",
            headers={"X-Moderator-Id": str(admin_moderator_id)},
        )
        
        # Если эндпоинта нет — будет 404
        # Если добавите — ожидайте 200
        if response.status_code == 404:
            pytest.skip("GET /blocking-reasons/{id} not implemented")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_reason.id)
        assert data["code"] == test_reason.code


# ==================== Run tests ====================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])