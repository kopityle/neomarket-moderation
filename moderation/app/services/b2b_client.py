import httpx
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
import asyncio

from app.config import settings
from app.schemas.b2b import (
    ModerationEventRequest,
    ModerationEventType,
    B2BProduct,
)


class B2BClient:
    """HTTP клиент для взаимодействия с B2B сервисом (по канону OpenAPI)"""
    
    def __init__(self):
        self.base_url = settings.B2B_SERVICE_URL
        self.timeout = settings.B2B_TIMEOUT
        self.service_key = settings.B2B_SERVICE_KEY
    
    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запросов к B2B"""
        return {
            "X-Service-Key": self.service_key,
            "Content-Type": "application/json",
        }
    
    async def get_product(self, product_id: UUID) -> Optional[B2BProduct]:
        """
        Получить товар из B2B по ID.
        GET /api/v1/public/products/{product_id}
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/public/products/{product_id}",
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    return B2BProduct(**response.json())
                elif response.status_code == 404:
                    return None
                else:
                    response.raise_for_status()
        except httpx.ConnectError:
            print(f"⚠️ Не удалось подключиться к B2B сервису: {self.base_url}")
            return None
        except Exception as e:
            print(f"⚠️ Ошибка при запросе к B2B: {e}")
            return None
    
    async def get_products_batch(self, product_ids: List[UUID]) -> List[B2BProduct]:
        """
        Получить несколько товаров из B2B по списку ID.
        POST /api/v1/public/products/batch
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/public/products/batch",
                    headers=self._get_headers(),
                    json={"product_ids": [str(pid) for pid in product_ids]},
                )
                
                if response.status_code == 200:
                    products_data = response.json()
                    return [B2BProduct(**p) for p in products_data]
                else:
                    response.raise_for_status()
        except Exception as e:
            print(f"⚠️ Ошибка при batch-запросе к B2B: {e}")
            return []
    
    async def send_moderation_event(self, event: ModerationEventRequest) -> bool:
        """
        Отправить событие модерации в B2B.
        POST /api/v1/moderation/events
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/moderation/events",
                    headers=self._get_headers(),
                    json=event.model_dump(mode="json", by_alias=True),
                )
                
                return response.status_code == 204
        except Exception as e:
            print(f"⚠️ Ошибка при отправке события модерации в B2B: {e}")
            return False
    
    async def get_sku(self, sku_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Получить SKU из B2B.
        GET /api/v1/public/skus/{sku_id}
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/public/skus/{sku_id}",
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    response.raise_for_status()
        except Exception as e:
            print(f"⚠️ Ошибка при запросе SKU из B2B: {e}")
            return None
    
    async def get_categories_tree(self) -> List[Dict[str, Any]]:
        """
        Получить дерево категорий из B2B.
        GET /api/v1/categories/tree
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/categories/tree",
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    response.raise_for_status()
        except Exception as e:
            print(f"⚠️ Ошибка при запросе категорий из B2B: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Проверка доступности B2B сервиса"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self._get_headers(),
                )
                return response.status_code == 200
        except Exception:
            return False


# ========== Синхронная обёртка для использования в синхронных эндпоинтах FastAPI ==========

class SyncB2BClient(B2BClient):
    """Синхронная обёртка для использования в синхронных эндпоинтах FastAPI"""
    
    def get_product_sync(self, product_id: UUID) -> Optional[B2BProduct]:
        """Синхронная обёртка для get_product"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если цикл уже запущен, создаём новую задачу
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.get_product(product_id))
                    return future.result()
            else:
                return asyncio.run(self.get_product(product_id))
        except RuntimeError:
            return asyncio.run(self.get_product(product_id))
    
    def send_moderation_event_sync(self, event: ModerationEventRequest) -> bool:
        """Синхронная обёртка для send_moderation_event"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.send_moderation_event(event))
                    return future.result()
            else:
                return asyncio.run(self.send_moderation_event(event))
        except RuntimeError:
            return asyncio.run(self.send_moderation_event(event))