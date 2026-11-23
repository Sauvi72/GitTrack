import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.models.student import Student
from app.models.pull_request import PullRequest
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.services.github_client import (
    GitHubClient,
    GitHubUserNotFoundError,
    GitHubRateLimitError,
    GitHubApiError
)
from app.api.sync import run_background_student_sync
from app.services.sync_service import SyncService

logger = logging.getLogger("opentrack.api.students")
router = APIRouter(prefix="/students", tags=["Students"])


def enrich_student_metrics(
    student: Student,
    db: Session,
    date_range: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> dict:
    """Calculates PR metrics for a student from stored database records, respecting optional date filters."""
    from app.services.analytics_service import get_timezone_bounds

    base_q = db.query(PullRequest).filter(PullRequest.student_id == student.id)

    if date_range or (date_from and date_to):
        start_utc, end_utc = get_timezone_bounds(
            date_range=date_range,
            date_from=date_from,
            date_to=date_to,
        )
        if start_utc:
            base_q = base_q.filter(PullRequest.created_at_github >= start_utc)
        if end_utc:
            base_q = base_q.filter(PullRequest.created_at_github <= end_utc)

    total = base_q.count()
    merged = base_q.filter(PullRequest.status == "MERGED").count()
    open_prs = base_q.filter(PullRequest.status == "OPEN").count()
    closed_unmerged = base_q.filter(PullRequest.status == "CLOSED_UNMERGED").count()

    merge_percentage = round((merged / total * 100.0), 1) if total > 0 else 0.0

    # Today's activity computed with timezone boundaries
    today_start, today_end = get_timezone_bounds(date_range="today")
    today_query = db.query(PullRequest).filter(
        PullRequest.student_id == student.id,
        PullRequest.created_at_github >= today_start,
        PullRequest.created_at_github <= today_end
    )
    prs_today = today_query.count()
    merged_today = today_query.filter(PullRequest.status == "MERGED").count()
    open_today = today_query.filter(PullRequest.status == "OPEN").count()
    closed_unmerged_today = today_query.filter(PullRequest.status == "CLOSED_UNMERGED").count()

    return {
        "id": student.id,
        "github_username": student.github_username,
        "github_user_id": student.github_user_id,
        "display_name": student.display_name,
        "profile_url": student.profile_url,
        "is_active": student.is_active,
        "created_at": student.created_at,
        "updated_at": student.updated_at,
        "last_synced_at": student.last_synced_at,
        "total_prs": total,
        "merged_prs": merged,
        "open_prs": open_prs,
        "closed_unmerged_prs": closed_unmerged,
        "merge_percentage": merge_percentage,
        "prs_today": prs_today,
        "merged_today": merged_today,
        "open_today": open_today,
        "closed_unmerged_today": closed_unmerged_today
    }


@router.get("", response_model=List[StudentResponse])
def get_students(
    q: Optional[str] = Query(None, description="Search by username or display name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    date_range: Optional[str] = Query(None, description="Timeframe filter (today, this_week, this_month, etc.)"),
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """Retrieve all students with their calculated contribution metrics."""
    query = db.query(Student)

    if is_active is not None:
        query = query.filter(Student.is_active == is_active)

    if q:
        search_filter = f"%{q.strip().lower()}%"
        query = query.filter(
            (func.lower(Student.github_username).like(search_filter)) |
            (func.lower(Student.display_name).like(search_filter))
        )

    students = query.order_by(Student.created_at.desc()).all()
    return [
        enrich_student_metrics(s, db, date_range=date_range, date_from=date_from, date_to=date_to)
        for s in students
    ]


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    background_tasks: BackgroundTasks,
    sync_now: bool = Query(False, description="Run initial full historical sync before returning"),
    db: Session = Depends(get_db),
    github_client: GitHubClient = Depends(lambda: GitHubClient())
):
    """
    Add a new student after validating their GitHub account via the GitHub API.
    Rejects duplicate usernames.
    If sync_now is True, immediately performs full initial synchronization before returning.
    Otherwise triggers full initial synchronization in the background ONLY for this new student.
    """
    clean_username = payload.github_username.strip()

    # Check duplicate
    existing = db.query(Student).filter(
        func.lower(Student.github_username) == clean_username.lower()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student with GitHub username '{clean_username}' already exists."
        )

    # Validate against GitHub API
    gh_user = None
    try:
        gh_user = github_client.get_user(clean_username)
    except GitHubUserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GitHub account '{clean_username}' was not found. Please verify the username."
        )
    except GitHubRateLimitError:
        # Graceful fallback: If GitHub rate limit is reached without a token, don't block the teacher
        logger.warning("GitHub rate limit reached during user validation. Adding student with profile URL.")
        gh_user = {
            "login": clean_username,
            "id": None,
            "name": payload.display_name or clean_username,
            "html_url": f"https://github.com/{clean_username}"
        }
    except GitHubApiError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to validate account with GitHub: {str(err)}"
        )

    student = Student(
        github_username=gh_user.get("login", clean_username),
        github_user_id=gh_user.get("id"),
        display_name=payload.display_name or gh_user.get("name"),
        profile_url=gh_user.get("html_url", f"https://github.com/{clean_username}"),
        is_active=True
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    if sync_now:
        try:
            service = SyncService(db=db, github_client=github_client)
            service.sync_student(student.id, force_full=True)
            db.refresh(student)
        except Exception as e:
            logger.warning("Initial sync during student creation: %s", e)
            background_tasks.add_task(run_background_student_sync, student.id, force_full=True)
    else:
        # Queue initial full historical synchronization in the background for THIS student only
        background_tasks.add_task(run_background_student_sync, student.id, force_full=True)

    return enrich_student_metrics(student, db)


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed information and metrics for an individual student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return enrich_student_metrics(student, db)


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db)
):
    """Update student information or toggle active status."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    if payload.display_name is not None:
        student.display_name = payload.display_name
    if payload.is_active is not None:
        student.is_active = payload.is_active

    db.commit()
    db.refresh(student)
    return enrich_student_metrics(student, db)


@router.delete("/{student_id}")
def delete_or_archive_student(
    student_id: int,
    hard_delete: bool = Query(False, description="Permanently delete instead of archiving"),
    db: Session = Depends(get_db)
):
    """
    Archive (soft-delete) or permanently remove a student.
    Archiving is preferred to retain historical contribution records.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    if hard_delete:
        db.delete(student)
        db.commit()
        return {"message": f"Student '{student.github_username}' permanently deleted."}
    else:
        student.is_active = False
        db.commit()
        return {"message": f"Student '{student.github_username}' archived successfully."}
