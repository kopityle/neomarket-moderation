from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.b2b_client import B2BClient
from app.services.moderation_service import ModerationService

router = APIRouter()


@router.post("/sync-product/{product_id}")
def sync_product_from_b2b(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Синхронизировать товар из B2B (вызывается по событию от B2B).
    Создаёт или обновляет задачу на модерацию.
    """
    # Получаем товар из B2B
    b2b_client = B2BClient()
    product = b2b_client.get_product(product_id)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Товар с ID {product_id} не найден в B2B"
        )
    
    # Создаём задачу на модерацию
    service = ModerationService(db)
    task = service.create_or_update_task(product)
    
    # Создаём снапшот товара
    service.create_snapshot(task.id, product, is_initial=True)
    
    return {"success": True, "task_id": task.id, "status": task.status}