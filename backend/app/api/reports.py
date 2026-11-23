import csv
import io
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database.session import get_db
from app.models.student import Student
from app.models.pull_request import PullRequest
from app.services.analytics_service import apply_date_filter

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/csv")
def export_contributions_csv(
    student_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Generate and stream a CSV file containing real Pull Request contribution records.
    """
    query = db.query(PullRequest).join(Student, PullRequest.student_id == Student.id)

    if student_id:
        query = query.filter(PullRequest.student_id == student_id)
    if status:
        query = query.filter(PullRequest.status == status.upper())

    query = apply_date_filter(query, PullRequest.created_at_github, date_from, date_to)
    prs = query.order_by(desc(PullRequest.created_at_github)).all()

    # Stream CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Headers
    writer.writerow([
        "PR ID",
        "Student Name",
        "Student GitHub Username",
        "Repository",
        "Organization",
        "PR Number",
        "Title",
        "Status",
        "GitHub State",
        "Draft",
        "Created At (UTC)",
        "Merged At (UTC)",
        "Closed At (UTC)",
        "Merged By",
        "Commits",
        "Additions",
        "Deletions",
        "Changed Files",
        "PR URL"
    ])

    for pr in prs:
        student_display = pr.student.display_name or pr.student.github_username if pr.student else "Unknown"
        student_uname = pr.student.github_username if pr.student else pr.author_username
        writer.writerow([
            pr.github_id,
            student_display,
            student_uname,
            pr.repository_full_name,
            pr.organization_name or "",
            pr.pr_number,
            pr.title,
            pr.status,
            pr.state,
            "Yes" if pr.is_draft else "No",
            pr.created_at_github.isoformat() if pr.created_at_github else "",
            pr.merged_at.isoformat() if pr.merged_at else "",
            pr.closed_at.isoformat() if pr.closed_at else "",
            pr.merged_by or "",
            pr.commits,
            pr.additions,
            pr.deletions,
            pr.changed_files,
            pr.html_url
        ])

    csv_data = output.getvalue()
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"opentrack_contributions_{timestamp_str}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache"
        }
    )


@router.get("/summary")
def get_reports_summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Summary metrics structured for printable or downloadable reports."""
    from app.services.analytics_service import AnalyticsService
    analytics = AnalyticsService(db)
    summary = analytics.get_dashboard_summary(date_from=date_from, date_to=date_to)
    leaderboard = analytics.get_leaderboard(limit=50, sort_by="merged")
    return {
        "summary": summary,
        "students": leaderboard,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
