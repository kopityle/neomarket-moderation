# app/api/moderation.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header, Response
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from app.config import settings
from app.models.reason import BlockingReason as BlockingReasonModel
from app.schemas.reason import BlockingReasonCreate, BlockingReasonUpdate, BlockingReason  

from app.database import get_db
from app.services.moderation_service import ModerationService
from app.schemas.task import (
    TicketResponse,
    TicketDetailResponse,
    PaginatedTickets,
    ClaimTicketRequest,
    BlockDecisionRequest,
    ApproveDecisionRequest,
    TaskStatus,
)
from app.schemas.reason import BlockingReasonResponse
from app.schemas.stats import StatsOverview, ModeratorStats
from app.schemas.b2b import IncomingB2BEvent
from app.api.dependencies import get_current_moderator_id, require_admin

router = APIRouter()


def check_ticket_not_hard_blocked(ticket, status_code: int = 403) -> None:
    """Проверить, что тикет не в HARD_BLOCKED"""
    if ticket.status == TaskStatus.HARD_BLOCKED.value:
        raise HTTPException(
            status_code=status_code,
            detail="Cannot modify HARD_BLOCKED ticket"
        )


# ==================== QUEUE ====================

@router.get("/queue", response_model=PaginatedTickets)
def get_queue(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    queue_priority: Optional[int] = Query(None, ge=1, le=4),
    category_id: Optional[UUID] = Query(None),
    seller_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
):
    """Просмотреть очередь тикетов."""
    service = ModerationService(db)
    tickets, total_count = service.get_queue(
        limit=limit,
        offset=offset,
        queue_priority=queue_priority,
        category_id=category_id,
        seller_id=seller_id,
    )
    return PaginatedTickets(
        items=tickets,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


@router.post("/queue/claim", response_model=TicketResponse, status_code=status.HTTP_200_OK)
def claim_ticket(
    request: Optional[ClaimTicketRequest] = None,
    moderator_id: UUID = Depends(get_current_moderator_id),
    db: Session = Depends(get_db),
):
    """Взять следующий тикет в работу."""
    service = ModerationService(db)
    
    active_ticket = service.get_moderator_active_ticket(moderator_id)
    if active_ticket:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active review ticket",
        )
    
    ticket = service.claim_next_ticket(
        moderator_id=moderator_id,
        queue_priority=request.queue_priority if request else None,
        category_ids=request.category_ids if request else None,
    )
    
    if not ticket:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    return ticket


# ==================== TICKETS ====================

@router.get("/tickets", response_model=PaginatedTickets)
def get_tickets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[TaskStatus] = Query(None),
    moderator_id: Optional[UUID] = Query(None),
    product_id: Optional[UUID] = Query(None),
    seller_id: Optional[UUID] = Query(None),
    created_from: Optional[str] = Query(None),
    created_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Список тикетов с фильтрами (history-view)."""
    service = ModerationService(db)
    tickets, total_count = service.get_tickets(
        limit=limit,
        offset=offset,
        status=status,
        moderator_id=moderator_id,
        product_id=product_id,
        seller_id=seller_id,
        created_from=created_from,
        created_to=created_to,
    )
    return PaginatedTickets(
        items=tickets,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
):
    """Карточка тикета с полной информацией."""
    service = ModerationService(db)
    ticket = service.get_ticket_detail(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found",
        )
    
    return ticket


@router.post("/tickets/{ticket_id}/release", response_model=TicketResponse)
def release_ticket(
    ticket_id: UUID,
    moderator_id: UUID = Depends(get_current_moderator_id),
    db: Session = Depends(get_db),
):
    """Вернуть тикет в очередь (отпустить)."""
    service = ModerationService(db)
    
    ticket = service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Защита от HARD_BLOCKED
    check_ticket_not_hard_blocked(ticket)
    
    result = service.release_ticket(ticket_id, moderator_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket is not in IN_REVIEW or belongs to another moderator",
        )
    
    return result


@router.post("/tickets/{ticket_id}/approve", response_model=TicketResponse)
def approve_ticket(
    ticket_id: UUID,
    request: Optional[ApproveDecisionRequest] = None,
    moderator_id: UUID = Depends(get_current_moderator_id),
    db: Session = Depends(get_db),
):
    """Одобрить тикет."""
    service = ModerationService(db)
    
    # 1. Проверка существования тикета
    ticket = service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # 2. Проверка на HARD_BLOCKED — возвращаем 409, а не 403!
    if ticket.status == TaskStatus.HARD_BLOCKED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,  # ← 409, не 403!
            detail="Cannot approve HARD_BLOCKED ticket"
        )
    
    # 3. Проверка статуса
    if ticket.status != TaskStatus.IN_REVIEW.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ticket is in {ticket.status} status, cannot approve"
        )
    
    # 4. Проверка прав
    if ticket.assigned_moderator_id != str(moderator_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket is not assigned to you"
        )
    
    # 5. Проверка наличия SKU
    has_skus = service.check_product_has_skus(UUID(ticket.product_id))
    if not has_skus:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product has no SKUs, cannot approve"
        )
    
    # 6. Проверка, что товар не изменён во время ревью
    if not service.check_product_not_changed_during_review(ticket):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product was edited during review. Please refresh and try again."
        )
    
    comment = request.comment if request else None
    result = service.approve_ticket(ticket_id, moderator_id, comment)
    
    return result

@router.post("/tickets/{ticket_id}/block", response_model=TicketResponse)
def block_ticket(
    ticket_id: UUID,
    request: BlockDecisionRequest,
    moderator_id: UUID = Depends(get_current_moderator_id),
    db: Session = Depends(get_db),
):
    """
    Заблокировать товар (soft или hard).
    Тип блокировки определяется по hard_block у выбранных BlockingReason.
    """
    service = ModerationService(db)
    
    # 1. Проверка существования тикета
    ticket = service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # 2. Нельзя блокировать уже HARD_BLOCKED
    if ticket.status == TaskStatus.HARD_BLOCKED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket is already HARD_BLOCKED"
        )
    
    # 3. Проверка статуса
    if ticket.status != TaskStatus.IN_REVIEW.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ticket is in {ticket.status} status, cannot block"
        )
    
    # 4. Проверка прав
    if ticket.assigned_moderator_id != str(moderator_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket is not assigned to you"
        )
    
    # 5. Валидация причин блокировки
    reasons = service.validate_blocking_reasons(request.blocking_reason_ids)
    if not reasons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid blocking_reason_ids"
        )
    
    # 6. Валидация field_reports
    if request.field_reports:
        invalid_fields = service.validate_field_reports(request.field_reports)
        if invalid_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid field paths: {invalid_fields}"
            )
    
    # 7. Блокируем тикет
    result = service.block_ticket(
        ticket_id=ticket_id,
        moderator_id=moderator_id,
        blocking_reason_ids=request.blocking_reason_ids,
        comment=request.comment,
        field_reports=request.field_reports,
    )
    
    return result


# ==================== BLOCKING REASONS ====================

@router.get("/blocking-reasons", response_model=List[BlockingReasonResponse])
def get_blocking_reasons(
    hard_block: Optional[bool] = Query(None, description="Фильтр по типу блокировки"),
    is_active: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    """Справочник причин блокировки"""
    service = ModerationService(db)
    return service.get_blocking_reasons(hard_block=hard_block, is_active=is_active)


@router.get("/blocking-reasons/{reason_id}", response_model=BlockingReasonResponse)
def get_blocking_reason_by_id(
    reason_id: UUID,
    db: Session = Depends(get_db),
):
    """Получить причину блокировки по ID"""
    service = ModerationService(db)
    reason = service.get_blocking_reason_by_id(reason_id)
    
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blocking reason with ID {reason_id} not found",
        )
    
    return reason


@router.post("/blocking-reasons", response_model=BlockingReasonResponse, status_code=status.HTTP_201_CREATED)
def create_blocking_reason(
    request: BlockingReasonCreate,
    db: Session = Depends(get_db),
    moderator_id: UUID = Depends(get_current_moderator_id),
    _: bool = Depends(require_admin),
):
    """Создать причину блокировки (только ADMIN)"""
    service = ModerationService(db)
    
    existing = db.query(BlockingReasonModel).filter(BlockingReasonModel.code == request.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Blocking reason with code {request.code} already exists",
        )
    
    reason = service.create_blocking_reason(request)
    return reason


@router.patch("/blocking-reasons/{reason_id}", response_model=BlockingReasonResponse)
def update_blocking_reason(
    reason_id: UUID,
    request: BlockingReasonUpdate,
    db: Session = Depends(get_db),
    moderator_id: UUID = Depends(get_current_moderator_id),
    _: bool = Depends(require_admin),
):
    """Обновить причину блокировки (только ADMIN)"""
    service = ModerationService(db)
    
    reason = service.update_blocking_reason(reason_id, request)
    
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blocking reason with ID {reason_id} not found",
        )
    
    return reason


@router.delete("/blocking-reasons/{reason_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_blocking_reason(
    reason_id: UUID,
    db: Session = Depends(get_db),
    moderator_id: UUID = Depends(get_current_moderator_id),
    _: bool = Depends(require_admin),
):
    """Деактивировать причину блокировки (soft-delete) (только ADMIN)"""
    service = ModerationService(db)
    success = service.deactivate_blocking_reason(reason_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blocking reason with ID {reason_id} not found",
        )
    
    return None

# ==================== STATS ====================

@router.get("/stats/overview", response_model=StatsOverview)
def get_stats_overview(
    period: str = Query(default="today", enum=["today", "week", "month"]),
    db: Session = Depends(get_db),
):
    """Сводка по очереди и решениям"""
    service = ModerationService(db)
    return service.get_stats_overview(period)


@router.get("/stats/moderators", response_model=List[ModeratorStats])
def get_moderator_stats(
    period: str = Query(default="week", enum=["today", "week", "month"]),
    db: Session = Depends(get_db),
):
    """Производительность модераторов"""
    service = ModerationService(db)
    return service.get_moderator_stats(period)


# ==================== B2B EVENTS (входящий канал) ====================

@router.post("/b2b/events", status_code=status.HTTP_202_ACCEPTED)
def receive_b2b_event(
    event: IncomingB2BEvent,
    x_service_key: str = Header(..., alias="X-Service-Key"),
    db: Session = Depends(get_db),
):
    """Приём событий о товарах от B2B-сервиса."""
    if x_service_key != settings.B2B_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Service-Key",
        )
    
    service = ModerationService(db)
    success = service.process_b2b_event(event)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate event (idempotency_key already used)",
        )
    
    return Response(status_code=status.HTTP_202_ACCEPTED)


