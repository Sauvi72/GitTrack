import datetime
import pytest
from app.models.student import Student
from app.models.pull_request import PullRequest


def test_dashboard_and_reports_flow(client, db_session):
    # 1. Create a student with PRs
    student = Student(
        github_username="reporter_student",
        github_user_id=999901,
        display_name="Reporter Student",
        profile_url="https://github.com/reporter_student",
        is_active=True
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    pr_merged = PullRequest(
        github_id=8001,
        github_node_id="PR_NODE_8001",
        student_id=student.id,
        repository_full_name="acme/web",
        repository_owner="acme",
        repository_name="web",
        organization_name="acme",
        pr_number=1,
        title="Merged Feature",
        html_url="https://github.com/acme/web/pull/1",
        state="closed",
        status="MERGED",
        is_draft=False,
        author_username="reporter_student",
        created_at_github=now - datetime.timedelta(days=2),
        merged_at=now - datetime.timedelta(days=1),
        merged_by="maintainer",
        commits=2,
        additions=100,
        deletions=10,
        changed_files=3,
        last_checked_at=now
    )

    pr_open = PullRequest(
        github_id=8002,
        github_node_id="PR_NODE_8002",
        student_id=student.id,
        repository_full_name="acme/web",
        repository_owner="acme",
        repository_name="web",
        organization_name="acme",
        pr_number=2,
        title="Open Fix",
        html_url="https://github.com/acme/web/pull/2",
        state="open",
        status="OPEN",
        is_draft=False,
        author_username="reporter_student",
        created_at_github=now - datetime.timedelta(hours=5),
        commits=1,
        additions=20,
        deletions=5,
        changed_files=1,
        last_checked_at=now
    )

    pr_unmerged = PullRequest(
        github_id=8003,
        github_node_id="PR_NODE_8003",
        student_id=student.id,
        repository_full_name="beta/api",
        repository_owner="beta",
        repository_name="api",
        organization_name="beta",
        pr_number=5,
        title="Closed without merge",
        html_url="https://github.com/beta/api/pull/5",
        state="closed",
        status="CLOSED_UNMERGED",
        is_draft=False,
        author_username="reporter_student",
        created_at_github=now - datetime.timedelta(days=5),
        closed_at=now - datetime.timedelta(days=4),
        commits=1,
        additions=5,
        deletions=5,
        changed_files=1,
        last_checked_at=now
    )

    db_session.add_all([pr_merged, pr_open, pr_unmerged])
    db_session.commit()

    # 2. Test /api/dashboard/summary
    res_summary = client.get("/api/dashboard/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["total_prs"] >= 3
    assert summary["merged_prs"] >= 1
    assert summary["open_prs"] >= 1
    assert summary["closed_unmerged_prs"] >= 1
    assert summary["merge_percentage"] > 0

    # 3. Test /api/dashboard/leaderboard
    res_board = client.get("/api/dashboard/leaderboard")
    assert res_board.status_code == 200
    board = res_board.json()
    assert len(board) >= 1
    assert any(s["github_username"] == "reporter_student" for s in board)

    # 4. Test /api/dashboard/activity
    res_act = client.get("/api/dashboard/activity?days=7")
    assert res_act.status_code == 200
    act = res_act.json()
    assert "timeline" in act
    assert "top_repositories" in act
    assert any(r["repository"] == "acme/web" for r in act["top_repositories"])

    # 5. Test /api/pull-requests with filtering and pagination
    res_prs = client.get("/api/pull-requests?status=MERGED")
    assert res_prs.status_code == 200
    prs_data = res_prs.json()
    assert prs_data["total"] >= 1
    assert all(item["status"] == "MERGED" for item in prs_data["items"])

    # 6. Test student statistics
    res_stat = client.get(f"/api/students/{student.id}/statistics")
    assert res_stat.status_code == 200
    stat = res_stat.json()
    assert stat["total_prs"] == 3
    assert stat["merged_prs"] == 1
    assert stat["open_prs"] == 1
    assert stat["closed_unmerged_prs"] == 1
    assert stat["merge_percentage"] == 33.3

    # 7. Test CSV export
    res_csv = client.get(f"/api/reports/csv?student_id={student.id}")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    csv_content = res_csv.text
    assert "PR ID,Student Name,Student GitHub Username" in csv_content
    assert "Merged Feature" in csv_content
    assert "Open Fix" in csv_content
