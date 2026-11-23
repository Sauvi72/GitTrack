import asyncio
import datetime
import logging
from typing import Optional, Dict, Any
from app.core.config import settings
from app.database.session import SessionLocal
from app.services.sync_service import SyncService

logger = logging.getLogger("opentrack.scheduler")

_scheduler_task: Optional[asyncio.Task] = None
_last_auto_sync_time: Optional[datetime.datetime] = None


async def background_sync_worker():
    """
    Periodic background worker that runs incremental sync for all active students
    every AUTO_SYNC_INTERVAL_MINUTES (default: 30 minutes).
    Runs in worker threads using asyncio.to_thread so the FastAPI event loop is never blocked.
    """
    global _last_auto_sync_time
    logger.info(
        "Automated background sync worker initialized (interval: %d minutes).",
        settings.AUTO_SYNC_INTERVAL_MINUTES
    )

    while True:
        try:
            # Wait for configured interval in seconds
            await asyncio.sleep(settings.AUTO_SYNC_INTERVAL_MINUTES * 60)

            if not settings.AUTO_SYNC_ENABLED:
                continue

            logger.info("Executing scheduled incremental synchronization for all active students...")

            def sync_job():
                db = SessionLocal()
                try:
                    service = SyncService(db=db)
                    return service.sync_all_active_students(force_full=False)
                finally:
                    db.close()

            results = await asyncio.to_thread(sync_job)
            _last_auto_sync_time = datetime.datetime.now(datetime.timezone.utc)
            successful = sum(1 for r in results if r.get("status") in ("SUCCESS", "PARTIAL"))
            logger.info(
                "Scheduled auto-sync completed: %d/%d students synchronized successfully.",
                successful,
                len(results)
            )

        except asyncio.CancelledError:
            logger.info("Automated background sync worker received shutdown signal.")
            break
        except Exception as e:
            logger.error("Error in scheduled auto-sync worker loop: %s", e, exc_info=True)
            # Sleep 30s before retrying to prevent rapid error cycling
            await asyncio.sleep(30)


def start_scheduler():
    """Start the background auto-sync task if enabled and not already running."""
    global _scheduler_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug("No running event loop to start background scheduler task.")
        return

    if settings.AUTO_SYNC_ENABLED and (_scheduler_task is None or _scheduler_task.done()):
        _scheduler_task = loop.create_task(background_sync_worker())
        logger.info("Auto-sync background task started.")


def stop_scheduler():
    """Cancel the background auto-sync task cleanly on shutdown."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("Auto-sync background task canceled.")


def get_auto_sync_status() -> Dict[str, Any]:
    """Return runtime metadata regarding the auto-sync scheduler."""
    is_running = False
    if _scheduler_task is not None:
        if hasattr(_scheduler_task, "cancelling") and _scheduler_task.cancelling():
            is_running = False
        else:
            is_running = not _scheduler_task.done()

    return {
        "enabled": settings.AUTO_SYNC_ENABLED,
        "interval_minutes": settings.AUTO_SYNC_INTERVAL_MINUTES,
        "is_running": is_running,
        "last_auto_sync_at": _last_auto_sync_time.isoformat() if _last_auto_sync_time else None
    }
