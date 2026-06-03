# app/schemas/__init__.py
from app.schemas.task import (
    ModerationTask,
    ModerationTaskCreate,
    ModerationTaskUpdate,
    ModerationTaskBase,
    TaskStatus,
    TaskKind,
    ClaimTicketRequest,
    BlockDecisionRequest,
    ApproveDecisionRequest,
    PaginatedTickets,
    TicketResponse,
    TicketDetailResponse,
)
from app.schemas.snapshot import (
    ProductSnapshot,
    ProductSnapshotCreate,
    ProductSnapshotBase,
    SnapshotType,
    TicketSnapshotsResponse,
    DiffEntry,
    # TicketHistoryEntry,  # ← УДАЛИТЬ ОТСЮДА
)
from app.schemas.decision import FieldReport, TicketHistoryEntry  # ← ДОБАВИТЬ СЮДА
from app.schemas.reason import (
    BlockingReason,
    BlockingReasonCreate,
    BlockingReasonUpdate,
    BlockingReasonBase,
    BlockingReasonResponse,
)
from app.schemas.comment import (
    ModerationComment,
    ModerationCommentCreate,
    ModerationCommentUpdate,
    ModerationCommentBase,
    PaginatedComments,
)
from app.schemas.stats import StatsOverview, ModeratorStats
from app.schemas.b2b import IncomingB2BEvent