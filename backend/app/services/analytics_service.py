import datetime
from typing import Dict, Any, List, Optional, Tuple
import zoneinfo
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case

from app.core.config import settings
from app.models.student import Student
from app.models.pull_request import PullRequest
from app.models.sync_log import SyncLog


def get_timezone_bounds(
    date_range: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tz_name: Optional[str] = None
) -> Tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
    """
    Computes [start_dt_utc_naive, end_dt_utc_naive] for SQL comparison based on
    calendar boundaries in the specified local timezone (default Asia/Kolkata).
    """
    tz_str = tz_name or settings.DEFAULT_TIMEZONE or "Asia/Kolkata"
    try:
        tz = zoneinfo.ZoneInfo(tz_str)
    except Exception:
        tz = zoneinfo.ZoneInfo("Asia/Kolkata")

    now_local = datetime.datetime.now(tz)
    start_local = None
    end_local = None

    normalized_range = (date_range or "").lower().strip()

    if normalized_range == "today":
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + datetime.timedelta(days=1)
    elif normalized_range in ("7d", "1w", "last_7_days", "last 7 days"):
        start_local = now_local - datetime.timedelta(days=7)
        end_local = now_local
    elif normalized_range in ("this_week", "this week"):
        # Local Monday 00:00:00
        monday = now_local - datetime.timedelta(days=now_local.weekday())
        start_local = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = now_local
    elif normalized_range in ("this_month", "this month"):
        start_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_local = now_local
    elif normalized_range in ("30d", "1m"):
        start_local = now_local - datetime.timedelta(days=30)
        end_local = now_local
    elif normalized_range == "90d":
        start_local = now_local - datetime.timedelta(days=90)
        end_local = now_local
    elif normalized_range in ("this_year", "this year"):
        start_local = now_local.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_local = now_local
    elif normalized_range == "1y":
        start_local = now_local - datetime.timedelta(days=365)
        end_local = now_local

    if date_from:
        try:
            # Parse YYYY-MM-DD or ISO
            if len(date_from) == 10:
                y, m, d = [int(p) for p in date_from.split("-")]
                start_local = datetime.datetime(y, m, d, 0, 0, 0, tzinfo=tz)
            else:
                dt = datetime.datetime.fromisoformat(date_from)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz)
                start_local = dt
        except Exception:
            pass

    if date_to:
        try:
            if len(date_to) == 10:
                y, m, d = [int(p) for p in date_to.split("-")]
                # End of day 23:59:59.999999
                end_local = datetime.datetime(y, m, d, 23, 59, 59, 999999, tzinfo=tz)
            else:
                dt = datetime.datetime.fromisoformat(date_to)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz)
                end_local = dt
        except Exception:
            pass

    start_utc = (
        start_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        if start_local is not None
        else None
    )
    end_utc = (
        end_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        if end_local is not None
        else None
    )

    return start_utc, end_utc


def apply_date_filter(
    query,
    date_column,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    date_range: Optional[str] = None,
    tz_name: Optional[str] = None
):
    """Apply UTC date bounds derived from local calendar boundaries."""
    start_utc, end_utc = get_timezone_bounds(
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
        tz_name=tz_name
    )

    if start_utc:
        query = query.filter(date_column >= start_utc)
    if end_utc:
        query = query.filter(date_column <= end_utc)

    return query


class AnalyticsService:
    """Service to compute platform-wide and student-specific contribution analytics locally from the DB."""

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_summary(
        self,
        date_range: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        filter_by: str = "created",
        tz: Optional[str] = None
    ) -> Dict[str, Any]:
        """Aggregate high-level contribution metrics strictly from the local database."""
        total_students = self.db.query(func.count(Student.id)).filter(Student.is_active == True).scalar() or 0

        date_col = PullRequest.merged_at if filter_by == "merged" else PullRequest.created_at_github

        # PR query with date filtering
        pr_query = self.db.query(PullRequest)
        pr_query = apply_date_filter(pr_query, date_col, date_from, date_to, date_range, tz_name=tz)

        total_prs = pr_query.count()
        merged_prs = pr_query.filter(PullRequest.status == "MERGED").count()
        open_prs = pr_query.filter(PullRequest.status == "OPEN").count()
        closed_unmerged_prs = pr_query.filter(PullRequest.status == "CLOSED_UNMERGED").count()

        merge_percentage = round((merged_prs / total_prs * 100.0), 1) if total_prs > 0 else 0.0

        # Distinct repositories & organizations in filtered window
        distinct_repos = pr_query.with_entities(PullRequest.repository_full_name).distinct().count()
        distinct_orgs = (
            pr_query.filter(PullRequest.organization_name.isnot(None))
            .with_entities(PullRequest.organization_name)
            .distinct()
            .count()
        )

        # Code churn metrics
        churn = (
            pr_query.with_entities(
                func.sum(PullRequest.additions).label("additions"),
                func.sum(PullRequest.deletions).label("deletions"),
                func.sum(PullRequest.changed_files).label("changed_files")
            ).first()
        )
        total_additions = int(churn.additions or 0) if churn else 0
        total_deletions = int(churn.deletions or 0) if churn else 0
        total_changed_files = int(churn.changed_files or 0) if churn else 0

        # Today metrics (computed with local timezone)
        today_start, today_end = get_timezone_bounds(date_range="today", tz_name=tz)
        today_prs_query = self.db.query(PullRequest).filter(
            PullRequest.created_at_github >= today_start,
            PullRequest.created_at_github <= today_end
        )
        prs_today = today_prs_query.count()
        merged_today = today_prs_query.filter(PullRequest.status == "MERGED").count()
        open_today = today_prs_query.filter(PullRequest.status == "OPEN").count()
        closed_unmerged_today = today_prs_query.filter(PullRequest.status == "CLOSED_UNMERGED").count()

        # Last synchronization
        last_sync = self.db.query(func.max(SyncLog.finished_at)).filter(SyncLog.status == "SUCCESS").scalar()

        return {
            "total_students": total_students,
            "total_prs": total_prs,
            "merged_prs": merged_prs,
            "open_prs": open_prs,
            "closed_unmerged_prs": closed_unmerged_prs,
            "merge_percentage": merge_percentage,
            "prs_today": prs_today,
            "merged_today": merged_today,
            "open_today": open_today,
            "closed_unmerged_today": closed_unmerged_today,
            "total_repositories": distinct_repos,
            "total_organizations": distinct_orgs,
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "total_changed_files": total_changed_files,
            "last_synced_at": last_sync.isoformat() if last_sync else None
        }

    def get_leaderboard(
        self,
        limit: int = 10,
        sort_by: str = "merged",
        date_range: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        tz_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Rank active students by merged PRs or total PRs within the specified date range."""
        students = self.db.query(Student).filter(Student.is_active == True).all()
        board = []

        start_utc, end_utc = get_timezone_bounds(
            date_range=date_range,
            date_from=date_from,
            date_to=date_to,
            tz_name=tz_name
        )
        today_start, today_end = get_timezone_bounds(date_range="today", tz_name=tz_name)

        for s in students:
            prs = self.db.query(PullRequest).filter(PullRequest.student_id == s.id)
            if start_utc:
                prs = prs.filter(PullRequest.created_at_github >= start_utc)
            if end_utc:
                prs = prs.filter(PullRequest.created_at_github <= end_utc)

            total = prs.count()
            merged = prs.filter(PullRequest.status == "MERGED").count()
            open_count = prs.filter(PullRequest.status == "OPEN").count()
            closed_unmerged = prs.filter(PullRequest.status == "CLOSED_UNMERGED").count()
            pct = round((merged / total * 100.0), 1) if total > 0 else 0.0

            # Today's PRs
            prs_today = self.db.query(PullRequest).filter(
                PullRequest.student_id == s.id,
                PullRequest.created_at_github >= today_start,
                PullRequest.created_at_github <= today_end
            ).count()

            board.append({
                "student_id": s.id,
                "github_username": s.github_username,
                "display_name": s.display_name or s.github_username,
                "profile_url": s.profile_url,
                "total_prs": total,
                "merged_prs": merged,
                "open_prs": open_count,
                "closed_unmerged_prs": closed_unmerged,
                "merge_percentage": pct,
                "prs_today": prs_today,
                "last_synced_at": s.last_synced_at.isoformat() if s.last_synced_at else None
            })

        if sort_by == "total":
            board.sort(key=lambda x: (x["total_prs"], x["merged_prs"]), reverse=True)
        else:
            board.sort(key=lambda x: (x["merged_prs"], x["total_prs"]), reverse=True)

        return board[:limit]

    def get_activity_timeline(
        self,
        days: Optional[int] = None,
        date_range: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        tz_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Group PR creation and merge events for charting, respecting date filters."""
        import calendar
        tz_str = tz_name or settings.DEFAULT_TIMEZONE or "Asia/Kolkata"
        try:
            tz = zoneinfo.ZoneInfo(tz_str)
        except Exception:
            tz = zoneinfo.ZoneInfo("Asia/Kolkata")

        now_local = datetime.datetime.now(tz)
        normalized_range = (date_range or "").lower().strip()

        # Case 1: Today -> 3-hour bins across today
        if normalized_range == "today":
            start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            end_local = start_local + datetime.timedelta(days=1)
            start_utc = start_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            end_utc = end_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)

            prs = self.db.query(PullRequest).filter(
                PullRequest.created_at_github >= start_utc,
                PullRequest.created_at_github <= end_utc
            ).all()

            timeline = []
            for h in range(0, 24, 3):
                bin_label = f"{h:02d}:00"
                bin_start_h = h
                bin_end_h = h + 3
                c_count = 0
                m_count = 0
                for pr in prs:
                    if pr.created_at_github:
                        pr_local = pr.created_at_github.replace(tzinfo=datetime.timezone.utc).astimezone(tz)
                        if bin_start_h <= pr_local.hour < bin_end_h:
                            c_count += 1
                            if pr.status == "MERGED":
                                m_count += 1
                timeline.append({
                    "date": bin_label,
                    "created": c_count,
                    "merged": m_count,
                    "closed_unmerged": 0
                })
            return timeline

        # Case 2: This Week -> daily from Monday to Sunday of current week
        elif normalized_range in ("this_week", "this week"):
            monday = now_local - datetime.timedelta(days=now_local.weekday())
            start_local = monday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_local = start_local + datetime.timedelta(days=7)
            start_utc = start_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            end_utc = end_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)

            prs = self.db.query(PullRequest).filter(
                PullRequest.created_at_github >= start_utc,
                PullRequest.created_at_github <= end_utc
            ).all()

            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            timeline = []
            for i in range(7):
                day_dt = start_local + datetime.timedelta(days=i)
                day_str = day_dt.date().isoformat()
                label = f"{day_names[i]} ({day_str[5:]})"
                c_count = 0
                m_count = 0
                for pr in prs:
                    if pr.created_at_github:
                        pr_local = pr.created_at_github.replace(tzinfo=datetime.timezone.utc).astimezone(tz)
                        if pr_local.date() == day_dt.date():
                            c_count += 1
                            if pr.status == "MERGED":
                                m_count += 1
                timeline.append({
                    "date": label,
                    "created": c_count,
                    "merged": m_count,
                    "closed_unmerged": 0
                })
            return timeline

        # Case 3: This Month -> days from day 1 to end of current month
        elif normalized_range in ("this_month", "this month"):
            start_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            _, num_days = calendar.monthrange(now_local.year, now_local.month)
            end_local = start_local + datetime.timedelta(days=num_days)
            start_utc = start_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            end_utc = end_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)

            prs = self.db.query(PullRequest).filter(
                PullRequest.created_at_github >= start_utc,
                PullRequest.created_at_github <= end_utc
            ).all()

            timeline = []
            for d in range(1, num_days + 1):
                day_dt = start_local.replace(day=d)
                day_str = day_dt.date().isoformat()
                c_count = 0
                m_count = 0
                for pr in prs:
                    if pr.created_at_github:
                        pr_local = pr.created_at_github.replace(tzinfo=datetime.timezone.utc).astimezone(tz)
                        if pr_local.date() == day_dt.date():
                            c_count += 1
                            if pr.status == "MERGED":
                                m_count += 1
                timeline.append({
                    "date": day_str,
                    "created": c_count,
                    "merged": m_count,
                    "closed_unmerged": 0
                })
            return timeline

        # Case 4: This Year -> 12 months (Jan..Dec)
        elif normalized_range in ("this_year", "this year"):
            start_local = now_local.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_local = now_local.replace(month=12, day=31, hour=23, minute=59, second=59)
            start_utc = start_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            end_utc = end_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)

            prs = self.db.query(PullRequest).filter(
                PullRequest.created_at_github >= start_utc,
                PullRequest.created_at_github <= end_utc
            ).all()

            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            timeline = []
            for m in range(1, 13):
                c_count = 0
                m_count = 0
                for pr in prs:
                    if pr.created_at_github:
                        pr_local = pr.created_at_github.replace(tzinfo=datetime.timezone.utc).astimezone(tz)
                        if pr_local.year == now_local.year and pr_local.month == m:
                            c_count += 1
                            if pr.status == "MERGED":
                                m_count += 1
                timeline.append({
                    "date": month_names[m - 1],
                    "created": c_count,
                    "merged": m_count,
                    "closed_unmerged": 0
                })
            return timeline

        # Case 5: Default / All Time / days=30
        effective_days = days or 30
        start_date = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=effective_days)
        ).date()

        prs = (
            self.db.query(PullRequest)
            .filter(PullRequest.created_at_github >= start_date)
            .all()
        )

        timeline_map: Dict[str, Dict[str, int]] = {}
        for i in range(effective_days + 1):
            day_str = (start_date + datetime.timedelta(days=i)).isoformat()
            timeline_map[day_str] = {"date": day_str, "created": 0, "merged": 0, "closed_unmerged": 0}

        for pr in prs:
            if pr.created_at_github:
                d_str = pr.created_at_github.date().isoformat()
                if d_str in timeline_map:
                    timeline_map[d_str]["created"] += 1
                    if pr.status == "MERGED":
                        timeline_map[d_str]["merged"] += 1
                    elif pr.status == "CLOSED_UNMERGED":
                        timeline_map[d_str]["closed_unmerged"] += 1

        return sorted(timeline_map.values(), key=lambda x: x["date"])

    def get_top_repositories(
        self,
        limit: int = 8,
        date_range: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        tz_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List repositories with the highest student PR counts within the specified date range."""
        start_utc, end_utc = get_timezone_bounds(
            date_range=date_range,
            date_from=date_from,
            date_to=date_to,
            tz_name=tz_name
        )
        query = self.db.query(
            PullRequest.repository_full_name,
            func.count(PullRequest.id).label("total"),
            func.sum(case((PullRequest.status == "MERGED", 1), else_=0)).label("merged")
        )
        if start_utc:
            query = query.filter(PullRequest.created_at_github >= start_utc)
        if end_utc:
            query = query.filter(PullRequest.created_at_github <= end_utc)

        rows = (
            query.group_by(PullRequest.repository_full_name)
            .order_by(desc("total"))
            .limit(limit)
            .all()
        )

        return [
            {
                "repository": r.repository_full_name,
                "total_prs": int(r.total),
                "merged_prs": int(r.merged or 0)
            }
            for r in rows
        ]

    def get_top_organizations(
        self,
        limit: int = 8,
        date_range: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        tz_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List organizations with the highest student PR counts within the specified date range."""
        start_utc, end_utc = get_timezone_bounds(
            date_range=date_range,
            date_from=date_from,
            date_to=date_to,
            tz_name=tz_name
        )
        query = self.db.query(
            PullRequest.organization_name,
            func.count(PullRequest.id).label("total"),
            func.sum(case((PullRequest.status == "MERGED", 1), else_=0)).label("merged")
        ).filter(PullRequest.organization_name.isnot(None))

        if start_utc:
            query = query.filter(PullRequest.created_at_github >= start_utc)
        if end_utc:
            query = query.filter(PullRequest.created_at_github <= end_utc)

        rows = (
            query.group_by(PullRequest.organization_name)
            .order_by(desc("total"))
            .limit(limit)
            .all()
        )

        return [
            {
                "organization": r.organization_name,
                "total_prs": int(r.total),
                "merged_prs": int(r.merged or 0)
            }
            for r in rows
        ]

    def get_student_statistics(
        self,
        student_id: int,
        date_range: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        filter_by: str = "created",
        tz: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates all 10 core metrics, breakdown by org and repo, daily timeline,
        and sync coverage status strictly from the local database.
        Zero GitHub API calls!
        """
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return {}

        start_utc, end_utc = get_timezone_bounds(
            date_range=date_range,
            date_from=date_from,
            date_to=date_to,
            tz_name=tz
        )

        # Base query for this student
        date_col = PullRequest.merged_at if filter_by == "merged" else PullRequest.created_at_github
        query = self.db.query(PullRequest).filter(PullRequest.student_id == student_id)
        if start_utc:
            query = query.filter(date_col >= start_utc)
        if end_utc:
            query = query.filter(date_col <= end_utc)

        prs = query.all()
        total = len(prs)
        merged = sum(1 for p in prs if p.status == "MERGED")
        open_count = sum(1 for p in prs if p.status == "OPEN")
        closed_unmerged = sum(1 for p in prs if p.status == "CLOSED_UNMERGED")
        pct = round((merged / total * 100.0), 1) if total > 0 else 0.0

        additions = sum(p.additions for p in prs)
        deletions = sum(p.deletions for p in prs)
        changed_files = sum(p.changed_files for p in prs)

        # 9. Number of PRs merged during the selected period (by merged_at)
        merged_in_period_query = self.db.query(PullRequest).filter(
            PullRequest.student_id == student_id,
            PullRequest.status == "MERGED",
            PullRequest.merged_at.isnot(None)
        )
        if start_utc:
            merged_in_period_query = merged_in_period_query.filter(PullRequest.merged_at >= start_utc)
        if end_utc:
            merged_in_period_query = merged_in_period_query.filter(PullRequest.merged_at <= end_utc)
        prs_merged_in_period = merged_in_period_query.count()

        # 10. Number of PRs currently open overall (across all time in DB)
        prs_currently_open_overall = self.db.query(PullRequest).filter(
            PullRequest.student_id == student_id,
            PullRequest.status == "OPEN"
        ).count()

        # Repositories breakdown in filtered window
        repo_map: Dict[str, Dict[str, Any]] = {}
        for p in prs:
            if p.repository_full_name not in repo_map:
                repo_map[p.repository_full_name] = {
                    "repository": p.repository_full_name,
                    "total": 0,
                    "merged": 0,
                    "open": 0,
                    "closed_unmerged": 0
                }
            repo_map[p.repository_full_name]["total"] += 1
            if p.status == "MERGED":
                repo_map[p.repository_full_name]["merged"] += 1
            elif p.status == "OPEN":
                repo_map[p.repository_full_name]["open"] += 1
            elif p.status == "CLOSED_UNMERGED":
                repo_map[p.repository_full_name]["closed_unmerged"] += 1

        # Organizations breakdown in filtered window
        org_map: Dict[str, Dict[str, Any]] = {}
        for p in prs:
            org = p.organization_name or "Independent / Personal"
            if org not in org_map:
                org_map[org] = {
                    "organization": org,
                    "total": 0,
                    "merged": 0,
                    "open": 0,
                    "closed_unmerged": 0
                }
            org_map[org]["total"] += 1
            if p.status == "MERGED":
                org_map[org]["merged"] += 1
            elif p.status == "OPEN":
                org_map[org]["open"] += 1
            elif p.status == "CLOSED_UNMERGED":
                org_map[org]["closed_unmerged"] += 1

        # Unique counts
        unique_repos = len(repo_map)
        unique_orgs = len([k for k in org_map.keys() if k != "Independent / Personal"])

        # 8. Daily creation timeline for the selected period
        timeline_buckets: Dict[str, Dict[str, int]] = {}
        for p in prs:
            dt = p.created_at_github
            if dt:
                day_str = dt.strftime("%Y-%m-%d")
                if day_str not in timeline_buckets:
                    timeline_buckets[day_str] = {"date": day_str, "created": 0, "merged": 0, "open": 0}
                timeline_buckets[day_str]["created"] += 1
                if p.status == "MERGED":
                    timeline_buckets[day_str]["merged"] += 1
                elif p.status == "OPEN":
                    timeline_buckets[day_str]["open"] += 1

        daily_timeline = sorted(timeline_buckets.values(), key=lambda x: x["date"])

        # Latest sync log details for coverage status
        latest_log = (
            self.db.query(SyncLog)
            .filter(SyncLog.student_id == student_id)
            .order_by(desc(SyncLog.started_at))
            .first()
        )
        total_stored_all_time = self.db.query(PullRequest).filter(PullRequest.student_id == student_id).count()

        sync_info = {
            "last_successful_sync": student.last_synced_at.isoformat() if student.last_synced_at else None,
            "last_attempted_sync": latest_log.started_at.isoformat() if latest_log else None,
            "status": latest_log.status if latest_log else "NEVER_SYNCED",
            "total_stored": total_stored_all_time,
            "new_prs": latest_log.new_pr_count if latest_log else 0,
            "updated_prs": latest_log.updated_pr_count if latest_log else 0,
            "is_complete": latest_log.is_complete if latest_log else True,
            "error_message": latest_log.error_message if latest_log else None
        }

        return {
            "student_id": student.id,
            "github_username": student.github_username,
            "display_name": student.display_name,
            "profile_url": student.profile_url,
            "is_active": student.is_active,
            "last_synced_at": student.last_synced_at.isoformat() if student.last_synced_at else None,
            "total_prs": total,
            "merged_prs": merged,
            "open_prs": open_count,
            "closed_unmerged_prs": closed_unmerged,
            "merge_percentage": pct,
            "unique_repositories": unique_repos,
            "unique_organizations": unique_orgs,
            "prs_merged_in_period": prs_merged_in_period,
            "prs_currently_open_overall": prs_currently_open_overall,
            "total_additions": additions,
            "total_deletions": deletions,
            "total_changed_files": changed_files,
            "filter_by": filter_by,
            "date_range": date_range,
            "repositories": sorted(repo_map.values(), key=lambda x: x["total"], reverse=True),
            "organizations": sorted(org_map.values(), key=lambda x: x["total"], reverse=True),
            "daily_timeline": daily_timeline,
            "sync_info": sync_info
        }
