import pytest
import datetime
from app.services.pr_processor import (
    classify_pr_status,
    parse_github_datetime,
    process_pull_request_payload,
    PRStatus
)


def test_classify_pr_status():
    # Rule 1: merged_at is not None -> MERGED, even if state is "closed"
    assert classify_pr_status("closed", "2025-01-01T00:00:00Z") == PRStatus.MERGED
    assert classify_pr_status("open", "2025-01-01T00:00:00Z") == PRStatus.MERGED

    # Rule 2: state is "open" and merged_at is None -> OPEN
    assert classify_pr_status("open", None) == PRStatus.OPEN

    # Rule 3: state is "closed" and merged_at is None -> CLOSED_UNMERGED
    assert classify_pr_status("closed", None) == PRStatus.CLOSED_UNMERGED
    assert classify_pr_status("", None) == PRStatus.CLOSED_UNMERGED


def test_parse_github_datetime():
    dt = parse_github_datetime("2025-02-14T15:30:45Z")
    assert dt is not None
    assert dt.year == 2025
    assert dt.month == 2
    assert dt.day == 14
    assert dt.hour == 15
    assert dt.minute == 30
    assert dt.second == 45

    assert parse_github_datetime(None) is None
    assert parse_github_datetime("invalid-date") is None


def test_process_pull_request_payload():
    mock_payload = {
        "id": 1234567,
        "node_id": "PR_kwDO123456",
        "number": 88,
        "title": "Add analytics export feature",
        "html_url": "https://github.com/my-org/core-repo/pull/88",
        "state": "closed",
        "merged_at": "2025-03-01T12:00:00Z",
        "merged_by": {"login": "lead-dev"},
        "draft": False,
        "created_at": "2025-02-28T09:00:00Z",
        "updated_at": "2025-03-01T12:05:00Z",
        "closed_at": "2025-03-01T12:00:00Z",
        "commits": 4,
        "additions": 250,
        "deletions": 30,
        "changed_files": 5,
        "comments": 3,
        "review_comments": 8,
        "base": {
            "ref": "main",
            "repo": {
                "name": "core-repo",
                "full_name": "my-org/core-repo",
                "owner": {"login": "my-org", "type": "Organization"}
            }
        },
        "head": {"ref": "feature/analytics"},
        "user": {"login": "student_coder", "id": 98765}
    }

    processed = process_pull_request_payload(mock_payload, student_id=1, author_username="student_coder")

    assert processed["github_id"] == 1234567
    assert processed["github_node_id"] == "PR_kwDO123456"
    assert processed["repository_full_name"] == "my-org/core-repo"
    assert processed["repository_owner"] == "my-org"
    assert processed["repository_name"] == "core-repo"
    assert processed["organization_name"] == "my-org"
    assert processed["pr_number"] == 88
    assert processed["status"] == PRStatus.MERGED
    assert processed["merged_by"] == "lead-dev"
    assert processed["commits"] == 4
    assert processed["additions"] == 250
    assert processed["deletions"] == 30
    assert processed["changed_files"] == 5
