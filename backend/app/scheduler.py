from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.db.session import SessionLocal
from app.services.pipeline import run_full_pipeline


def build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="UTC")

    async def job() -> None:
        db = SessionLocal()
        try:
            await run_full_pipeline(db)
        finally:
            db.close()

    scheduler.add_job(job, "interval", minutes=settings.recompute_interval_minutes, id="groundtrack-pass-recompute")
    return scheduler
