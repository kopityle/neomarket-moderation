from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.services.moderation_service import ModerationService
from app.schemas.task import ModerationTask
from app.schemas.decision import ModerationDecisionCreate
from app.schemas.reason import BlockingReason
from app.schemas.b2b import B2BProduct
from app.api.dependencies import get_current_moderator_id

router = APIRouter()


@router.post("/get-next", response_model=Optional[B2BProduct])
def get_next_product_for_moderation(
    priority: Optional[int] = Query(default=None, ge=0, le=1, description="Приоритет: 0=обычный, 1=высокий"),
    moderator_id: UUID = Depends(get_current_moderator_id),
    db: Session = Depends(get_db)
):
    """
    Получить следующий товар на модерацию.
    Возвращает товар из B2B и создаёт снапшот.
    """
    service = ModerationService(db)
    result = service.get_next_task(moderator_id, priority)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Нет товаров на модерацию"
        )
    
    return result


@router.post("/products/{product_id}/approve", response_model=dict)
def approve_product(
    product_id: int,
    moderator_id: UUID = Depends(get_current_moderator_id),
    db: Session = Depends(get_db)
):
    """
    Одобрить товар.
    Отправляет результат в B2B и обновляет статус задачи.
    """
    service = ModerationService(db)
    result = service.approve_product(product_id, moderator_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Товар с ID {product_id} не найден в очереди модерации"
        )
    
    return {"success": True, "product_id": product_id, "decision": "APPROVED"}


@router.post("/products/{product_id}/decline", response_model=dict)
def decline_product(
    product_id: int,
    reason_id: int = Query(..., description="ID причины блокировки"),
    comment: Optional[str] = Query(None, max_length=1000),
    moderator_id: UUID = Depends(get_current_moderator_id),
    db: Session = Depends(get_db)
):
    """
    Заблокировать товар с указанием причины.
    Отправляет результат в B2B и обновляет статус задачи.
    """
    service = ModerationService(db)
    result = service.decline_product(product_id, moderator_id, reason_id, comment)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Товар с ID {product_id} не найден в очереди модерации"
        )
    
    return {"success": True, "product_id": product_id, "decision": "DECLINED"}


@router.get("/product-blocking-reasons", response_model=List[BlockingReason])
def get_blocking_reasons(
    is_active: bool = True,
    db: Session = Depends(get_db)
):
    """
    Получить список причин блокировки.
    """
    service = ModerationService(db)
    return service.get_blocking_reasons(is_active)