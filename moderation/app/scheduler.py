# app/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.moderation_service import ModerationService
from app.database import SessionLocal

async def release_expired_job():
    """Асинхронная задача для освобождения просроченных тикетов"""
    db = SessionLocal()
    try:
        service = ModerationService(db)
        count = service.release_expired_tickets()
        if count:
            print(f"Released {count} expired tickets")
    finally:
        db.close()

# Используем AsyncIOScheduler вместо BackgroundScheduler
scheduler = AsyncIOScheduler()
scheduler.add_job(release_expired_job, 'interval', minutes=5)