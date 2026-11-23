import pytest
from app.services.github_client import (
    GitHubClient,
    GitHubUserNotFoundError,
    GitHubRateLimitError,
    GitHubApiError
)


def test_build_query():
    client = GitHubClient()
    # Global public query
    q1 = client.build_query(author="octocat", scope_type="global")
    assert q1 == "is:pr author:octocat"

    # Organization query
    q2 = client.build_query(author="octocat", scope_type="organization", scope_value="google")
    assert q2 == "is:pr author:octocat org:google"

    # Repository query
    q3 = client.build_query(author="octocat", scope_type="repository", scope_value="facebook/react")
    assert q3 == "is:pr author:octocat repo:facebook/react"

    # Date range query
    q4 = client.build_query(author="octocat", date_from="2025-01-01", date_to="2025-06-30")
    assert q4 == "is:pr author:octocat created:2025-01-01..2025-06-30"


def test_get_user_success(monkeypatch):
    client = GitHubClient()

    class MockResponse:
        status_code = 200
        is_success = True
        headers = {"x-ratelimit-remaining": "4999"}

        def json(self):
            return {
                "login": "octocat",
                "id": 583231,
                "node_id": "MDQ6VXNlcjU4MzIzMQ==",
                "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
                "html_url": "https://github.com/octocat",
                "name": "The Octocat"
            }

    monkeypatch.setattr("httpx.Client.request", lambda self, *args, **kwargs: MockResponse())

    user = client.get_user("octocat")
    assert user["login"] == "octocat"
    assert user["id"] == 583231
    assert user["name"] == "The Octocat"


def test_get_user_not_found(monkeypatch):
    client = GitHubClient()

    class MockResponse:
        status_code = 404
        is_success = False
        text = "Not Found"
        headers = {}

    monkeypatch.setattr("httpx.Client.request", lambda self, *args, **kwargs: MockResponse())

    with pytest.raises(GitHubUserNotFoundError):
        client.get_user("nonexistent-user-123456789")


def test_rate_limit_handling(monkeypatch):
    client = GitHubClient()

    class MockResponse:
        status_code = 403
        is_success = False
        text = "API rate limit exceeded for user ID 123"
        headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1700000000"}

    monkeypatch.setattr("httpx.Client.request", lambda self, *args, **kwargs: MockResponse())

    with pytest.raises(GitHubRateLimitError) as exc_info:
        client.get_user("anyuser")
    assert exc_info.value.reset_time == 1700000000


def test_search_pull_requests(monkeypatch):
    client = GitHubClient()

    class MockResponse:
        status_code = 200
        is_success = True
        headers = {"x-ratelimit-remaining": "29"}

        def json(self):
            return {
                "total_count": 2,
                "incomplete_results": False,
                "items": [
                    {
                        "id": 1001,
                        "node_id": "PR_kwDO1234",
                        "number": 42,
                        "title": "Fix memory leak in parser",
                        "pull_request": {"url": "https://api.github.com/repos/org/repo/pulls/42"},
                        "repository_url": "https://api.github.com/repos/org/repo"
                    }
                ]
            }

    monkeypatch.setattr("httpx.Client.request", lambda self, *args, **kwargs: MockResponse())

    results = client.search_pull_requests("is:pr author:student1")
    assert results["total_count"] == 2
    assert len(results["items"]) == 1
    assert results["items"][0]["title"] == "Fix memory leak in parser"


def test_get_pull_request_details(monkeypatch):
    client = GitHubClient()

    class MockResponse:
        status_code = 200
        is_success = True
        headers = {}

        def json(self):
            return {
                "id": 99999,
                "node_id": "PR_node_test",
                "number": 10,
                "title": "Feature: Add Dark Mode",
                "html_url": "https://github.com/owner/repo/pull/10",
                "state": "closed",
                "merged_at": "2025-02-15T10:30:00Z",
                "merged_by": {"login": "maintainer"},
                "commits": 3,
                "additions": 150,
                "deletions": 20,
                "changed_files": 4,
                "base": {"ref": "main", "repo": {"name": "repo", "full_name": "owner/repo", "owner": {"login": "owner"}}},
                "head": {"ref": "dark-mode"},
                "comments": 2,
                "review_comments": 5,
                "user": {"login": "student1", "id": 12345}
            }

    monkeypatch.setattr("httpx.Client.request", lambda self, *args, **kwargs: MockResponse())

    details = client.get_pull_request_details("owner", "repo", 10)
    assert details["id"] == 99999
    assert details["merged_at"] == "2025-02-15T10:30:00Z"
    assert details["merged_by"]["login"] == "maintainer"
    assert details["commits"] == 3
