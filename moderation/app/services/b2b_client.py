import httpx
from typing import Optional, Dict, Any
from app.config import settings


class B2BClient:
    """HTTP клиент для взаимодействия с B2B сервисом"""
    
    def __init__(self):
        self.base_url = settings.B2B_SERVICE_URL
        self.timeout = settings.B2B_TIMEOUT
    
    async def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Получить товар из B2B по ID"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/products/{product_id}")
                
                if response.status_code == 200:
                    return response.json()
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
    
    async def send_moderation_result(
        self, 
        product_id: int, 
        decision: str, 
        reason_id: Optional[int] = None,
        comment: Optional[str] = None
    ) -> bool:
        """Отправить результат модерации в B2B"""
        payload = {
            "product_id": product_id,
            "decision": decision,
            "blocking_reason_id": reason_id,
            "comment": comment
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/internal/moderation-callback",
                    json=payload
                )
                return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Ошибка при отправке результата в B2B: {e}")
            return False