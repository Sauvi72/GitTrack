import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func

from app.database.session import get_db
from app.models.student import Student
from app.models.pull_request import PullRequest
from app.schemas.pull_request import PullRequestResponse
from app.services.analytics_service import AnalyticsService, apply_date_filter

logger = logging.getLogger("opentrack.api.pull_requests")
router = APIRouter(tags=["Pull Requests"])


@router.get("/pull-requests")
def list_pull_requests(
    student_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None, description="OPEN, MERGED, or CLOSED_UNMERGED"),
    organization: Optional[str] = Query(None),
    repository: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    date_range: Optional[str] = Query(None),
    filter_by: str = Query("created", description="created or merged"),
    tz: Optional[str] = Query(None, description="Timezone name, defaults to Asia/Kolkata"),
    sort_by: str = Query("created", description="created, merged, repository, or additions"),
    order: str = Query("desc", description="asc or desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Search and filter pull requests across all students with pagination.
    Queries the local database directly.
    """
    query = db.query(PullRequest)

    if student_id:
        query = query.filter(PullRequest.student_id == student_id)
    if status:
        query = query.filter(PullRequest.status == status.upper())
    if organization:
        query = query.filter(func.lower(PullRequest.organization_name) == organization.lower().strip())
    if repository:
        query = query.filter(func.lower(PullRequest.repository_full_name) == repository.lower().strip())

    date_col = PullRequest.merged_at if filter_by == "merged" else PullRequest.created_at_github
    query = apply_date_filter(query, date_col, date_from, date_to, date_range, tz_name=tz)

    total_count = query.count()

    # Sorting
    sort_col = PullRequest.created_at_github
    if sort_by == "merged":
        sort_col = PullRequest.merged_at
    elif sort_by == "repository":
        sort_col = PullRequest.repository_full_name
    elif sort_by == "additions":
        sort_col = PullRequest.additions

    if order.lower() == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    return {
        "items": [PullRequestResponse.model_validate(p) for p in items],
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }


@router.get("/students/{student_id}/pull-requests")
def get_student_pull_requests(
    student_id: int,
    status: Optional[str] = Query(None),
    organization: Optional[str] = Query(None),
    repository: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    date_range: Optional[str] = Query(None),
    filter_by: str = Query("created"),
    tz: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieve PR history for a specific student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    return list_pull_requests(
        student_id=student_id,
        status=status,
        organization=organization,
        repository=repository,
        date_from=date_from,
        date_to=date_to,
        date_range=date_range,
        filter_by=filter_by,
        tz=tz,
        page=page,
        limit=limit,
        db=db
    )


@router.get("/students/{student_id}/statistics")
def get_student_statistics(
    student_id: int,
    date_range: Optional[str] = Query(None, description="today, 7d, this_week, this_month, this_year, all"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    filter_by: str = Query("created", description="created or merged"),
    tz: Optional[str] = Query(None, description="Timezone name, defaults to Asia/Kolkata"),
    db: Session = Depends(get_db)
):
    """Retrieve comprehensive statistics and breakdowns for a specific student from the local database."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    analytics = AnalyticsService(db)
    return analytics.get_student_statistics(
        student_id=student_id,
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
        filter_by=filter_by,
        tz=tz
    )
