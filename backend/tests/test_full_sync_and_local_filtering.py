import datetime
from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.pull_request import PullRequest
from app.models.sync_log import SyncLog
from app.services.sync_service import SyncService
from app.services.analytics_service import AnalyticsService, get_timezone_bounds


def test_initial_full_sync_and_storage(db_session: Session):
    """
    Test Step 1-3:
    Perform initial historical synchronization, verify PRs are stored in the database
    with all accurate timestamps and metadata.
    """
    student = Student(
        github_username="testdev_full",
        display_name="Test Dev Full",
        profile_url="https://github.com/testdev_full",
        is_active=True
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    # Mock GitHubClient
    mock_gh = MagicMock()
    # Mock PR Discovery returning 3 items across different dates
    now = datetime.datetime.now(datetime.timezone.utc)
    today_dt = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    three_days_ago_dt = (now - datetime.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    forty_days_ago_dt = (now - datetime.timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_gh.search_pull_requests.return_value = {
        "total_count": 3,
        "incomplete_results": False,
        "items": [
            {
                "number": 101,
                "repository_url": "https://api.github.com/repos/org-alpha/repo-one",
                "pull_request": {"url": "https://api.github.com/repos/org-alpha/repo-one/pulls/101"}
            },
            {
                "number": 102,
                "repository_url": "https://api.github.com/repos/org-alpha/repo-one",
                "pull_request": {"url": "https://api.github.com/repos/org-alpha/repo-one/pulls/102"}
            },
            {
                "number": 201,
                "repository_url": "https://api.github.com/repos/org-beta/repo-two",
                "pull_request": {"url": "https://api.github.com/repos/org-beta/repo-two/pulls/201"}
            }
        ]
    }

    # Mock PR details
    def get_details(owner, repo, number):
        if number == 101:
            return {
                "id": 10001,
                "node_id": "PR_NODE_101",
                "number": 101,
                "title": "PR Created Today",
                "html_url": "https://github.com/org-alpha/repo-one/pull/101",
                "state": "open",
                "draft": False,
                "user": {"login": "testdev_full", "id": 999},
                "created_at": today_dt,
                "updated_at": today_dt,
                "closed_at": None,
                "merged_at": None,
                "base": {"repo": {"name": "repo-one", "full_name": "org-alpha/repo-one", "owner": {"login": "org-alpha", "type": "Organization"}}, "ref": "main"},
                "head": {"ref": "feat-today"},
                "commits": 2,
                "additions": 45,
                "deletions": 5,
                "changed_files": 3,
                "comments": 1,
                "review_comments": 0
            }
        elif number == 102:
            return {
                "id": 10002,
                "node_id": "PR_NODE_102",
                "number": 102,
                "title": "PR Merged 3 Days Ago",
                "html_url": "https://github.com/org-alpha/repo-one/pull/102",
                "state": "closed",
                "draft": False,
                "user": {"login": "testdev_full", "id": 999},
                "created_at": three_days_ago_dt,
                "updated_at": three_days_ago_dt,
                "closed_at": three_days_ago_dt,
                "merged_at": three_days_ago_dt,
                "merged_by": {"login": "maintainer_a"},
                "base": {"repo": {"name": "repo-one", "full_name": "org-alpha/repo-one", "owner": {"login": "org-alpha", "type": "Organization"}}, "ref": "main"},
                "head": {"ref": "feat-3days"},
                "commits": 1,
                "additions": 100,
                "deletions": 20,
                "changed_files": 4,
                "comments": 2,
                "review_comments": 1
            }
        else:
            return {
                "id": 10003,
                "node_id": "PR_NODE_201",
                "number": 201,
                "title": "PR 40 Days Ago Closed Unmerged",
                "html_url": "https://github.com/org-beta/repo-two/pull/201",
                "state": "closed",
                "draft": False,
                "user": {"login": "testdev_full", "id": 999},
                "created_at": forty_days_ago_dt,
                "updated_at": forty_days_ago_dt,
                "closed_at": forty_days_ago_dt,
                "merged_at": None,
                "base": {"repo": {"name": "repo-two", "full_name": "org-beta/repo-two", "owner": {"login": "org-beta", "type": "Organization"}}, "ref": "main"},
                "head": {"ref": "feat-old"},
                "commits": 3,
                "additions": 10,
                "deletions": 50,
                "changed_files": 2,
                "comments": 0,
                "review_comments": 0
            }

    mock_gh.get_pull_request_details.side_effect = get_details

    sync_service = SyncService(db=db_session, github_client=mock_gh)
    res = sync_service.sync_student(student.id, force_full=True)

    assert res["status"] == "SUCCESS"
    assert res["sync_type"] == "FULL"
    assert res["new_prs"] == 3
    assert res["updated_prs"] == 0

    # Verify records stored in database
    stored = db_session.query(PullRequest).filter(PullRequest.student_id == student.id).all()
    assert len(stored) == 3

    p101 = next(p for p in stored if p.pr_number == 101)
    assert p101.status == "OPEN"
    assert p101.created_at_github is not None
    assert p101.last_checked_at is not None

    p102 = next(p for p in stored if p.pr_number == 102)
    assert p102.status == "MERGED"
    assert p102.merged_by == "maintainer_a"
    assert p102.merged_at is not None

    p201 = next(p for p in stored if p.pr_number == 201)
    assert p201.status == "CLOSED_UNMERGED"


def test_local_date_based_filtering_zero_github_calls(db_session: Session):
    """
    Test Step 4-12:
    Verify that changing filters (today, 7d, this_month, this_year, all)
    computes stats strictly from the local DB with ZERO GitHub API calls.
    """
    student = db_session.query(Student).filter(Student.github_username == "testdev_full").first()
    assert student is not None

    analytics = AnalyticsService(db_session)

    # 1. Today filter
    stats_today = analytics.get_student_statistics(student.id, date_range="today")
    assert stats_today["total_prs"] == 1
    assert stats_today["open_prs"] == 1
    assert stats_today["merged_prs"] == 0

    # 2. Last 7 Days filter
    stats_7d = analytics.get_student_statistics(student.id, date_range="7d")
    assert stats_7d["total_prs"] == 2  # PR 101 (today) and PR 102 (3 days ago)
    assert stats_7d["merged_prs"] == 1
    assert stats_7d["open_prs"] == 1
    assert stats_7d["closed_unmerged_prs"] == 0

    # 3. All Time filter
    stats_all = analytics.get_student_statistics(student.id, date_range="")
    assert stats_all["total_prs"] == 3
    assert stats_all["merged_prs"] == 1
    assert stats_all["open_prs"] == 1
    assert stats_all["closed_unmerged_prs"] == 1
    assert stats_all["merge_percentage"] == 33.3
    assert stats_all["unique_repositories"] == 2
    assert stats_all["unique_organizations"] == 2
    assert stats_all["prs_currently_open_overall"] == 1

    # Repository breakdown respects date filter
    # In 7d window, only repo-one exists!
    assert len(stats_7d["repositories"]) == 1
    assert stats_7d["repositories"][0]["repository"] == "org-alpha/repo-one"
    assert stats_7d["repositories"][0]["total"] == 2

    # In All Time window, both repositories exist
    assert len(stats_all["repositories"]) == 2


def test_incremental_sync_updates_open_pr_without_duplicates(db_session: Session):
    """
    Test Step 13-16:
    Incremental sync:
    1. Previously open PR (101) has now been merged on GitHub.
    2. A new PR (103) has also been created.
    Verify that PR 101 is updated to MERGED, PR 103 is added as new,
    and NO duplicates are created!
    """
    student = db_session.query(Student).filter(Student.github_username == "testdev_full").first()
    assert student is not None

    now = datetime.datetime.now(datetime.timezone.utc)
    today_dt = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_gh = MagicMock()
    # Search returns newly created PR 103
    mock_gh.search_pull_requests.return_value = {
        "total_count": 1,
        "incomplete_results": False,
        "items": [
            {
                "number": 103,
                "repository_url": "https://api.github.com/repos/org-alpha/repo-one",
                "pull_request": {"url": "https://api.github.com/repos/org-alpha/repo-one/pulls/103"}
            }
        ]
    }

    def get_details(owner, repo, number):
        if number == 101:
            # PR 101 has now been merged!
            return {
                "id": 10001,
                "node_id": "PR_NODE_101",
                "number": 101,
                "title": "PR Created Today (Now Merged)",
                "html_url": "https://github.com/org-alpha/repo-one/pull/101",
                "state": "closed",
                "draft": False,
                "user": {"login": "testdev_full", "id": 999},
                "created_at": today_dt,
                "updated_at": today_dt,
                "closed_at": today_dt,
                "merged_at": today_dt,
                "merged_by": {"login": "lead_dev"},
                "base": {"repo": {"name": "repo-one", "full_name": "org-alpha/repo-one", "owner": {"login": "org-alpha", "type": "Organization"}}, "ref": "main"},
                "head": {"ref": "feat-today"},
                "commits": 3,
                "additions": 60,
                "deletions": 10,
                "changed_files": 4,
                "comments": 2,
                "review_comments": 1
            }
        elif number == 103:
            # PR 103 is a brand new PR
            return {
                "id": 10004,
                "node_id": "PR_NODE_103",
                "number": 103,
                "title": "Brand New PR",
                "html_url": "https://github.com/org-alpha/repo-one/pull/103",
                "state": "open",
                "draft": False,
                "user": {"login": "testdev_full", "id": 999},
                "created_at": today_dt,
                "updated_at": today_dt,
                "closed_at": None,
                "merged_at": None,
                "base": {"repo": {"name": "repo-one", "full_name": "org-alpha/repo-one", "owner": {"login": "org-alpha", "type": "Organization"}}, "ref": "main"},
                "head": {"ref": "feat-brand-new"},
                "commits": 1,
                "additions": 15,
                "deletions": 0,
                "changed_files": 1,
                "comments": 0,
                "review_comments": 0
            }
        raise ValueError(f"Unexpected PR number: {number}")

    mock_gh.get_pull_request_details.side_effect = get_details

    sync_service = SyncService(db=db_session, github_client=mock_gh)
    # Perform incremental sync
    res = sync_service.sync_student(student.id, force_full=False)

    assert res["status"] == "SUCCESS"
    assert res["sync_type"] == "INCREMENTAL"
    assert res["new_prs"] == 1      # Only PR 103 is new
    assert res["updated_prs"] == 1  # PR 101 was updated from OPEN -> MERGED

    # Check database counts
    total_stored = db_session.query(PullRequest).filter(PullRequest.student_id == student.id).count()
    assert total_stored == 4  # 3 original + 1 new. NO DUPLICATES!

    # Verify PR 101 is now MERGED in database
    p101 = db_session.query(PullRequest).filter(
        PullRequest.student_id == student.id,
        PullRequest.pr_number == 101
    ).first()
    assert p101.status == "MERGED"
    assert p101.merged_by == "lead_dev"

    # Verify local stats reflect the update immediately
    analytics = AnalyticsService(db_session)
    stats = analytics.get_student_statistics(student.id, date_range="")
    assert stats["total_prs"] == 4
    assert stats["merged_prs"] == 2  # 101 and 102
    assert stats["open_prs"] == 1    # 103
    assert stats["closed_unmerged_prs"] == 1
    assert stats["prs_currently_open_overall"] == 1
