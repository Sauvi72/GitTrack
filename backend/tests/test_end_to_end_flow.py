import pytest
from app.services.github_client import GitHubClient


class EndToEndMockGitHubClient(GitHubClient):
    """Simulates live GitHub responses for end-to-end workflow."""
    def __init__(self):
        super().__init__(token="test-e2e-token")

    def get_user(self, username: str):
        if username == "ada_lovelace":
            return {
                "login": "ada_lovelace",
                "id": 18151210,
                "html_url": "https://github.com/ada_lovelace",
                "name": "Ada Lovelace"
            }
        raise Exception("User not found")

    def search_pull_requests(self, query: str, page: int = 1, per_page: int = 100, **kwargs):
        # Discovers 3 PRs: 1 merged, 1 open, 1 closed unmerged
        return {
            "total_count": 3,
            "incomplete_results": False,
            "items": [
                {
                    "id": 901,
                    "node_id": "NODE_PR_901",
                    "number": 101,
                    "title": "Add Analytical Engine algorithm",
                    "pull_request": {"url": "https://api.github.com/repos/computing/engine/pulls/101"},
                    "repository_url": "https://api.github.com/repos/computing/engine"
                },
                {
                    "id": 902,
                    "node_id": "NODE_PR_902",
                    "number": 102,
                    "title": "Refactor Bernoulli number computation",
                    "pull_request": {"url": "https://api.github.com/repos/computing/engine/pulls/102"},
                    "repository_url": "https://api.github.com/repos/computing/engine"
                },
                {
                    "id": 903,
                    "node_id": "NODE_PR_903",
                    "number": 15,
                    "title": "Experimental punch card format",
                    "pull_request": {"url": "https://api.github.com/repos/heritage/punchcards/pulls/15"},
                    "repository_url": "https://api.github.com/repos/heritage/punchcards"
                }
            ]
        }

    def get_pull_request_details(self, owner: str, repo: str, pull_number: int):
        if pull_number == 101:
            return {
                "id": 901,
                "node_id": "NODE_PR_901",
                "number": 101,
                "title": "Add Analytical Engine algorithm",
                "html_url": "https://github.com/computing/engine/pull/101",
                "state": "closed",
                "merged_at": "2025-05-10T12:00:00Z",
                "merged_by": {"login": "babbage"},
                "draft": False,
                "created_at": "2025-05-01T10:00:00Z",
                "updated_at": "2025-05-10T12:00:00Z",
                "closed_at": "2025-05-10T12:00:00Z",
                "commits": 5,
                "additions": 340,
                "deletions": 20,
                "changed_files": 4,
                "comments": 2,
                "review_comments": 4,
                "base": {"ref": "main", "repo": {"name": "engine", "full_name": "computing/engine", "owner": {"login": "computing", "type": "Organization"}}},
                "head": {"ref": "feature/algo"},
                "user": {"login": "ada_lovelace", "id": 18151210}
            }
        elif pull_number == 102:
            return {
                "id": 902,
                "node_id": "NODE_PR_902",
                "number": 102,
                "title": "Refactor Bernoulli number computation",
                "html_url": "https://github.com/computing/engine/pull/102",
                "state": "open",
                "merged_at": None,
                "merged_by": None,
                "draft": False,
                "created_at": "2025-05-15T09:00:00Z",
                "updated_at": "2025-05-16T10:00:00Z",
                "closed_at": None,
                "commits": 2,
                "additions": 50,
                "deletions": 10,
                "changed_files": 2,
                "comments": 1,
                "review_comments": 0,
                "base": {"ref": "main", "repo": {"name": "engine", "full_name": "computing/engine", "owner": {"login": "computing", "type": "Organization"}}},
                "head": {"ref": "fix/bernoulli"},
                "user": {"login": "ada_lovelace", "id": 18151210}
            }
        else:
            return {
                "id": 903,
                "node_id": "NODE_PR_903",
                "number": 15,
                "title": "Experimental punch card format",
                "html_url": "https://github.com/heritage/punchcards/pull/15",
                "state": "closed",
                "merged_at": None,
                "merged_by": None,
                "draft": False,
                "created_at": "2025-04-01T08:00:00Z",
                "updated_at": "2025-04-02T08:00:00Z",
                "closed_at": "2025-04-02T08:00:00Z",
                "commits": 1,
                "additions": 15,
                "deletions": 5,
                "changed_files": 1,
                "comments": 3,
                "review_comments": 1,
                "base": {"ref": "main", "repo": {"name": "punchcards", "full_name": "heritage/punchcards", "owner": {"login": "heritage", "type": "Organization"}}},
                "head": {"ref": "experiment"},
                "user": {"login": "ada_lovelace", "id": 18151210}
            }


def test_complete_teacher_workflow_end_to_end(client, monkeypatch):
    # Setup mock github client
    mock_gh = EndToEndMockGitHubClient()
    monkeypatch.setattr(GitHubClient, "get_user", lambda self, u: mock_gh.get_user(u))
    monkeypatch.setattr(GitHubClient, "search_pull_requests", lambda self, *args, **kwargs: mock_gh.search_pull_requests(*args, **kwargs))
    monkeypatch.setattr(GitHubClient, "get_pull_request_details", lambda self, o, r, p: mock_gh.get_pull_request_details(o, r, p))

    # STEP 1: Teacher logs in
    login_res = client.post("/api/auth/login", json={
        "email": "test_teacher@opentrack.edu",
        "password": "TestPass123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # STEP 2: Teacher verifies their account
    me_res = client.get("/api/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "test_teacher@opentrack.edu"

    # STEP 3: Teacher adds a student
    add_res = client.post("/api/students", json={
        "github_username": "ada_lovelace",
        "display_name": "Ada Lovelace"
    }, headers=auth_headers)
    assert add_res.status_code == 201
    student = add_res.json()
    student_id = student["id"]
    assert student["github_user_id"] == 18151210

    # STEP 4: Teacher configures tracking scopes (adds organization scope)
    scope_res = client.post("/api/scopes", json={
        "scope_type": "organization",
        "scope_value": "computing",
        "display_name": "Computing Org"
    }, headers=auth_headers)
    assert scope_res.status_code == 201

    # STEP 5: Teacher initiates synchronization
    sync_res = client.post(f"/api/students/{student_id}/sync?background=false", headers=auth_headers)
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["status"] == "SUCCESS"
    assert sync_data["details"]["discovered"] == 3
    assert sync_data["details"]["new_prs"] == 3

    # STEP 6: Verify PR Classification in Database
    # Expected: 1 Merged, 1 Open, 1 Closed Unmerged
    stat_res = client.get(f"/api/students/{student_id}/statistics", headers=auth_headers)
    assert stat_res.status_code == 200
    stats = stat_res.json()
    assert stats["total_prs"] == 3
    assert stats["merged_prs"] == 1
    assert stats["open_prs"] == 1
    assert stats["closed_unmerged_prs"] == 1
    assert stats["merge_percentage"] == 33.3

    # STEP 7: Check Dashboard Metrics
    dashboard_res = client.get("/api/dashboard/summary", headers=auth_headers)
    assert dashboard_res.status_code == 200
    summary = dashboard_res.json()
    assert summary["total_prs"] >= 3
    assert summary["merged_prs"] >= 1
    assert summary["open_prs"] >= 1
    assert summary["closed_unmerged_prs"] >= 1

    # STEP 8: Check Leaderboard
    leaderboard_res = client.get("/api/dashboard/leaderboard", headers=auth_headers)
    assert leaderboard_res.status_code == 200
    board = leaderboard_res.json()
    assert any(s["github_username"] == "ada_lovelace" for s in board)

    # STEP 9: Test Idempotency (Repeat sync)
    sync2_res = client.post(f"/api/students/{student_id}/sync?background=false", headers=auth_headers)
    assert sync2_res.status_code == 200
    sync2_data = sync2_res.json()
    assert sync2_data["details"]["new_prs"] == 0
    assert sync2_data["details"]["updated_prs"] == 3

    # Total PR count remains exactly 3
    stat2_res = client.get(f"/api/students/{student_id}/statistics", headers=auth_headers)
    assert stat2_res.json()["total_prs"] == 3

    # STEP 10: Teacher views PR list and links
    prs_res = client.get(f"/api/pull-requests?student_id={student_id}", headers=auth_headers)
    assert prs_res.status_code == 200
    prs = prs_res.json()["items"]
    assert len(prs) == 3
    for pr in prs:
        assert pr["html_url"].startswith("https://github.com/")
        assert pr["status"] in ("MERGED", "OPEN", "CLOSED_UNMERGED")

    # STEP 11: Teacher exports CSV report
    csv_res = client.get(f"/api/reports/csv?student_id={student_id}", headers=auth_headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "ada_lovelace" in csv_res.text
    assert "Add Analytical Engine algorithm" in csv_res.text
