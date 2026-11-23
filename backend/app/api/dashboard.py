import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger("opentrack.api.dashboard")
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    date_range: Optional[str] = Query(None, description="7d, 30d, 90d, 1y, or all"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Platform-wide summary metrics for students, PRs, merge percentage, and code changes."""
    analytics = AnalyticsService(db)
    return analytics.get_dashboard_summary(
        date_range=date_range,
        date_from=date_from,
        date_to=date_to
    )


@router.get("/leaderboard")
def get_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    sort_by: str = Query("merged", description="'merged' or 'total'"),
    date_range: Optional[str] = Query(None, description="today, this_week, this_month, this_year, or all"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Rank students by merged PRs or total PR contributions within selected date range."""
    analytics = AnalyticsService(db)
    return analytics.get_leaderboard(
        limit=limit,
        sort_by=sort_by,
        date_range=date_range,
        date_from=date_from,
        date_to=date_to
    )


@router.get("/activity")
def get_dashboard_activity(
    days: Optional[int] = Query(None),
    date_range: Optional[str] = Query(None, description="today, this_week, this_month, this_year, or all"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Contribution timeline, top repositories, and top organizations for dashboard charts, respecting date filters."""
    analytics = AnalyticsService(db)
    return {
        "timeline": analytics.get_activity_timeline(
            days=days,
            date_range=date_range,
            date_from=date_from,
            date_to=date_to
        ),
        "top_repositories": analytics.get_top_repositories(
            limit=8,
            date_range=date_range,
            date_from=date_from,
            date_to=date_to
        ),
        "top_organizations": analytics.get_top_organizations(
            limit=8,
            date_range=date_range,
            date_from=date_from,
            date_to=date_to
        )
    }
