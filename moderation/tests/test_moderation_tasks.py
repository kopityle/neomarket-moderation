import pytest
from uuid import uuid4


class TestModerationTasks:
    """Тесты для задач модерации"""
    
    def test_get_next_task_no_tasks(self, client, test_moderator_id):
        """Нет задач на модерацию"""
        response = client.post(
            "/api/v1/product-moderation/get-next",
            headers={"X-Moderator-Id": test_moderator_id}
        )
        assert response.status_code == 404
    
    def test_get_next_task_success(self, client, test_moderation_task, test_moderator_id, test_product_id):
        """Успешное получение следующей задачи"""
        response = client.post(
            "/api/v1/product-moderation/get-next",
            headers={"X-Moderator-Id": test_moderator_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Сравниваем как строки (UUID)
        assert str(data["id"]) == str(test_product_id)
    
    def test_approve_product_not_found(self, client, test_moderator_id):
        """Одобрение несуществующего товара"""
        fake_id = "99999999-9999-9999-9999-999999999999"
        response = client.post(
            f"/api/v1/product-moderation/products/{fake_id}/approve",
            headers={"X-Moderator-Id": test_moderator_id}
        )
        assert response.status_code == 404
    
    def test_approve_product_success(self, client, test_moderation_task_in_progress, test_moderator_id, test_product_id):
        """Успешное одобрение товара"""
        response = client.post(
            f"/api/v1/product-moderation/products/{test_product_id}/approve",
            headers={"X-Moderator-Id": test_moderator_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["decision"] == "APPROVED"
    
    def test_decline_product_success(self, client, test_moderation_task_in_progress, test_moderator_id, test_blocking_reasons, test_product_id):
        """Успешная блокировка товара"""
        reason = test_blocking_reasons[0]
        
        response = client.post(
            f"/api/v1/product-moderation/products/{test_product_id}/decline",
            params={"reason_id": reason.id, "comment": "Неверные фотографии"},
            headers={"X-Moderator-Id": test_moderator_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["decision"] == "DECLINED"
    
    def test_decline_product_missing_reason(self, client, test_moderation_task_in_progress, test_moderator_id, test_product_id):
        """Блокировка без указания причины"""
        response = client.post(
            f"/api/v1/product-moderation/products/{test_product_id}/decline",
            params={"comment": "Комментарий без причины"},
            headers={"X-Moderator-Id": test_moderator_id}
        )
        assert response.status_code in [400, 422]
    
    def test_moderation_without_auth(self, client):
        """Запрос без авторизации"""
        response = client.post("/api/v1/product-moderation/get-next")
        assert response.status_code in [400, 422]
    
    def test_invalid_moderator_id(self, client):
        """Неверный формат ID модератора"""
        response = client.post(
            "/api/v1/product-moderation/get-next",
            headers={"X-Moderator-Id": "invalid-uuid"}
        )
        assert response.status_code in [400, 422]