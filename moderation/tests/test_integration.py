import pytest
from unittest.mock import patch, AsyncMock


class TestModerationIntegration:
    """Интеграционные тесты Moderation"""
    
    @pytest.mark.skip(reason="B2B сервис не запущен")
    def test_full_moderation_flow(self, client, test_moderator_id, test_blocking_reasons):
        """Полный цикл модерации (требует B2B)"""
        # 1. Создаём задачу (имитируем событие от B2B)
        # 2. Модератор получает следующую задачу
        # 3. Модератор одобряет/блокирует
        # 4. Проверяем, что результат отправлен в B2B
        pass
    
    def test_blocking_reasons_endpoint_performance(self, client):
        """Тест производительности эндпоинта причин блокировки"""
        import time
        
        start = time.time()
        for _ in range(10):
            response = client.get("/api/v1/product-moderation/product-blocking-reasons")
            assert response.status_code == 200
        end = time.time()
        
        assert (end - start) < 2.0  # 10 запросов за 2 секунды