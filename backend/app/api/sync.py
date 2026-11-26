import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database.session import get_db, SessionLocal
from app.models.student import Student
from app.models.sync_log import SyncLog
from app.schemas.sync import SyncTriggerResponse, SyncLogResponse
from app.services.sync_service import SyncService, StudentAlreadySyncingError, _active_sync_locks, _lock_mutex
from app.services.scheduler import get_auto_sync_status

logger = logging.getLogger("opentrack.api.sync")
router = APIRouter(tags=["Synchronization"])


def run_background_student_sync(student_id: int, force_full: bool = False):
    """Worker task executed in background thread."""
    db = SessionLocal()
    try:
        service = SyncService(db=db)
        service.sync_student(student_id, force_full=force_full)
    except Exception as e:
        logger.error("Background sync failed for student %d: %s", student_id, e)
    finally:
        db.close()


def run_background_sync_all(force_full: bool = False):
    """Worker task for synchronizing all students in background."""
    db = SessionLocal()
    try:
        service = SyncService(db=db)
        service.sync_all_active_students(force_full=force_full)
    except Exception as e:
        logger.error("Background sync-all failed: %s", e)
    finally:
        db.close()


@router.post("/students/{student_id}/sync", response_model=SyncTriggerResponse)
def sync_student(
    student_id: int,
    force_full: bool = Query(False, description="Force full historical sync instead of incremental"),
    background: bool = Query(False, description="Run as background task"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Trigger PR discovery and detail collection for a single student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    if background:
        background_tasks.add_task(run_background_student_sync, student_id, force_full)
        return {
            "message": f"Synchronization scheduled in background for '{student.github_username}'.",
            "student_id": student_id,
            "status": "QUEUED"
        }

    try:
        service = SyncService(db=db)
        result = service.sync_student(student_id, force_full=force_full)
        return {
            "message": f"Synchronization completed for '{student.github_username}'.",
            "student_id": student_id,
            "status": result["status"],
            "details": result
        }
    except StudentAlreadySyncingError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Sync failed: {str(e)}")


@router.post("/sync-all")
def sync_all(
    force_full: bool = Query(False, description="Force full historical sync for all students"),
    background: bool = Query(True, description="Run as background task (default true for bulk)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Trigger synchronization for all active students."""
    if background:
        background_tasks.add_task(run_background_sync_all, force_full)
        return {"message": "Bulk synchronization scheduled in background.", "status": "QUEUED"}

    service = SyncService(db=db)
    results = service.sync_all_active_students(force_full=force_full)
    return {"message": "Bulk synchronization finished.", "results": results}


@router.get("/sync-logs", response_model=List[SyncLogResponse])
def get_sync_logs(
    student_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieve audit history of synchronization runs."""
    query = db.query(SyncLog)
    if student_id:
        query = query.filter(SyncLog.student_id == student_id)
    if status:
        query = query.filter(SyncLog.status == status)

    return query.order_by(desc(SyncLog.started_at)).limit(limit).all()


@router.get("/sync-status")
def get_sync_status(db: Session = Depends(get_db)):
    """Check whether synchronization jobs are actively running."""
    with _lock_mutex:
        active_count = len(_active_sync_locks)
        active_ids = list(_active_sync_locks)

    last_log = db.query(SyncLog).order_by(desc(SyncLog.started_at)).first()

    return {
        "is_syncing": active_count > 0,
        "active_students_syncing": active_ids,
        "auto_sync": get_auto_sync_status(),
        "last_sync": {
            "id": last_log.id,
            "status": last_log.status,
            "started_at": last_log.started_at.isoformat(),
            "finished_at": last_log.finished_at.isoformat() if last_log.finished_at else None,
            "new_prs": last_log.new_pr_count or 0,
            "updated_prs": last_log.updated_pr_count or 0,
            "is_complete": bool(last_log.is_complete) if last_log.is_complete is not None else True
        } if last_log else None
    }
