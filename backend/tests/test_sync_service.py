import pytest
from app.models.student import Student
from app.models.pull_request import PullRequest
from app.models.tracking_scope import TrackingScope
from app.models.sync_log import SyncLog
from app.services.sync_service import SyncService
from app.services.github_client import GitHubClient


class MockGitHubClient(GitHubClient):
    """Mock GitHub client returning deterministic PR data."""
    def __init__(self):
        super().__init__(token="mock-token")

    def search_pull_requests(self, query: str, page: int = 1, per_page: int = 100, **kwargs):
        return {
            "total_count": 2,
            "incomplete_results": False,
            "items": [
                {
                    "id": 201,
                    "node_id": "NODE_PR_201",
                    "number": 1,
                    "title": "Initial commit PR",
                    "pull_request": {"url": "https://api.github.com/repos/orgA/repoA/pulls/1"},
                    "repository_url": "https://api.github.com/repos/orgA/repoA"
                },
                {
                    "id": 202,
                    "node_id": "NODE_PR_202",
                    "number": 2,
                    "title": "Bug fix in calculator",
                    "pull_request": {"url": "https://api.github.com/repos/orgB/repoB/pulls/2"},
                    "repository_url": "https://api.github.com/repos/orgB/repoB"
                }
            ]
        }

    def get_pull_request_details(self, owner: str, repo: str, pull_number: int):
        if pull_number == 1:
            return {
                "id": 201,
                "node_id": "NODE_PR_201",
                "number": 1,
                "title": "Initial commit PR",
                "html_url": "https://github.com/orgA/repoA/pull/1",
                "state": "closed",
                "merged_at": "2025-01-10T12:00:00Z",
                "merged_by": {"login": "mentor1"},
                "draft": False,
                "created_at": "2025-01-09T10:00:00Z",
                "updated_at": "2025-01-10T12:00:00Z",
                "closed_at": "2025-01-10T12:00:00Z",
                "commits": 2,
                "additions": 45,
                "deletions": 5,
                "changed_files": 2,
                "comments": 1,
                "review_comments": 2,
                "base": {"ref": "main", "repo": {"name": "repoA", "full_name": "orgA/repoA", "owner": {"login": "orgA", "type": "Organization"}}},
                "head": {"ref": "feature-1"},
                "user": {"login": "sync_student_1", "id": 8888}
            }
        else:
            return {
                "id": 202,
                "node_id": "NODE_PR_202",
                "number": 2,
                "title": "Bug fix in calculator",
                "html_url": "https://github.com/orgB/repoB/pull/2",
                "state": "open",
                "merged_at": None,
                "merged_by": None,
                "draft": False,
                "created_at": "2025-02-01T08:00:00Z",
                "updated_at": "2025-02-01T08:30:00Z",
                "closed_at": None,
                "commits": 1,
                "additions": 10,
                "deletions": 2,
                "changed_files": 1,
                "comments": 0,
                "review_comments": 0,
                "base": {"ref": "main", "repo": {"name": "repoB", "full_name": "orgB/repoB", "owner": {"login": "orgB", "type": "Organization"}}},
                "head": {"ref": "bugfix"},
                "user": {"login": "sync_student_1", "id": 8888}
            }


def test_sync_service_idempotency_and_deduplication(db_session):
    # 1. Create a student in database
    student = Student(
        github_username="sync_student_1",
        github_user_id=8888,
        display_name="Sync Test Student",
        profile_url="https://github.com/sync_student_1",
        is_active=True
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    # 2. Ensure tracking scopes: check if global exists, add org scope if not present
    scope_global = db_session.query(TrackingScope).filter(TrackingScope.scope_value == "*").first()
    if not scope_global:
        scope_global = TrackingScope(scope_type="global", scope_value="*", display_name="Global", is_active=True)
        db_session.add(scope_global)
    
    scope_org = db_session.query(TrackingScope).filter(TrackingScope.scope_value == "orgA").first()
    if not scope_org:
        scope_org = TrackingScope(scope_type="organization", scope_value="orgA", display_name="Org A", is_active=True)
        db_session.add(scope_org)
    db_session.commit()

    # 3. First Sync execution
    mock_client = MockGitHubClient()
    service = SyncService(db=db_session, github_client=mock_client)
    res1 = service.sync_student(student.id)

    assert res1["status"] == "SUCCESS"
    assert res1["discovered"] == 2
    assert res1["new_prs"] == 2
    assert res1["updated_prs"] == 0

    # Verify database has exactly 2 PRs
    prs_run1 = db_session.query(PullRequest).filter(PullRequest.student_id == student.id).all()
    assert len(prs_run1) == 2

    pr1 = next(p for p in prs_run1 if p.pr_number == 1)
    pr2 = next(p for p in prs_run1 if p.pr_number == 2)
    assert pr1.status == "MERGED"
    assert pr2.status == "OPEN"

    # Verify student last_synced_at is updated
    db_session.refresh(student)
    assert student.last_synced_at is not None

    # 4. Second Sync execution (Idempotency Check)
    # The exact same sync should not create duplicates, new_prs should be 0, updated_prs should be 2
    res2 = service.sync_student(student.id)
    assert res2["status"] == "SUCCESS"
    assert res2["new_prs"] == 0
    assert res2["updated_prs"] == 2

    # Verify database STILL has exactly 2 PRs
    prs_run2 = db_session.query(PullRequest).filter(PullRequest.student_id == student.id).all()
    assert len(prs_run2) == 2

    # Verify sync logs were created
    logs = db_session.query(SyncLog).filter(SyncLog.student_id == student.id).all()
    assert len(logs) == 2
    assert all(log.status == "SUCCESS" for log in logs)
