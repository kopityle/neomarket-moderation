from app.models.reason import BlockingReason

class TestBlockingReasons:
    """Тесты для причин блокировки"""
    
    def test_get_blocking_reasons_list(self, client, test_blocking_reasons):
        """Получение списка причин блокировки"""
        response = client.get("/api/v1/product-moderation/product-blocking-reasons")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 3
        assert data[0]["code"] == "wrong_photos"
        assert data[0]["name"] == "Неверные фотографии"
    
    def test_get_blocking_reasons_only_active(self, client, db_session, test_blocking_reasons):
        """Получение только активных причин блокировки"""
        # Деактивируем одну причину
        reason = db_session.query(BlockingReason).filter_by(code="wrong_price").first()
        reason.is_active = False
        db_session.commit()
        
        response = client.get("/api/v1/product-moderation/product-blocking-reasons?is_active=true")
        assert response.status_code == 200
        
        data = response.json()
        # Должны быть только активные причины
        assert all(r["is_active"] is True for r in data)
    
    def test_get_blocking_reasons_structure(self, client, test_blocking_reasons):
        """Проверка структуры ответа причин блокировки"""
        response = client.get("/api/v1/product-moderation/product-blocking-reasons")
        assert response.status_code == 200
        
        data = response.json()
        first_reason = data[0]
        
        # Проверяем наличие всех полей
        assert "id" in first_reason
        assert "code" in first_reason
        assert "name" in first_reason
        assert "description" in first_reason
        assert "is_active" in first_reason
        assert "created_at" in first_reason