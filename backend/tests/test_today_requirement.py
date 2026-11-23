import datetime
import pytest
from app.models.student import Student
from app.models.pull_request import PullRequest
from app.services.github_client import GitHubClient


def test_track_accounts_and_see_prs_created_today_with_all_details(client, db_session, monkeypatch):
    """
    Direct test for the user's requirement:
    - Track any GitHub accounts of choice.
    - See how many Pull Requests each account has created today.
    - Inspect the status of each PR (merged, open, or closed).
    - Inspect which organizations and repositories those PRs were submitted to.
    - Inspect all other relevant details (title, code changes, links, dates).
    """
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    today_morning = now - datetime.timedelta(minutes=5)
    today_noon = now - datetime.timedelta(minutes=3)
    today_afternoon = now - datetime.timedelta(minutes=1)
    five_days_ago = now - datetime.timedelta(days=5)

    # 1. Track Account A: frontend_dev_student
    student_a = Student(
        github_username="frontend_dev_student",
        github_user_id=101001,
        display_name="Alex (Frontend Lead)",
        profile_url="https://github.com/frontend_dev_student",
        is_active=True
    )

    # Track Account B: backend_dev_student
    student_b = Student(
        github_username="backend_dev_student",
        github_user_id=101002,
        display_name="Jordan (Backend Specialist)",
        profile_url="https://github.com/backend_dev_student",
        is_active=True
    )

    db_session.add_all([student_a, student_b])
    db_session.commit()
    db_session.refresh(student_a)
    db_session.refresh(student_b)

    # 2. Add PRs created TODAY for Student A:
    # PR 1: MERGED, repo facebook/react, org facebook
    pr_a1_today = PullRequest(
        github_id=701,
        github_node_id="PR_NODE_701",
        student_id=student_a.id,
        repository_full_name="facebook/react",
        repository_owner="facebook",
        repository_name="react",
        organization_name="facebook",
        pr_number=28001,
        title="Fix Suspense boundary re-render loop",
        html_url="https://github.com/facebook/react/pull/28001",
        state="closed",
        status="MERGED",
        is_draft=False,
        author_username="frontend_dev_student",
        author_github_id=student_a.github_user_id,
        created_at_github=today_morning,
        updated_at_github=today_noon,
        closed_at=today_noon,
        merged_at=today_noon,
        merged_by="gaearon",
        base_branch="main",
        head_branch="fix-suspense",
        commits=3,
        additions=142,
        deletions=18,
        changed_files=4,
        comments=5,
        review_comments=8,
        last_checked_at=now
    )

    # PR 2: OPEN, repo vercel/next.js, org vercel
    pr_a2_today = PullRequest(
        github_id=702,
        github_node_id="PR_NODE_702",
        student_id=student_a.id,
        repository_full_name="vercel/next.js",
        repository_owner="vercel",
        repository_name="next.js",
        organization_name="vercel",
        pr_number=55102,
        title="Optimize app router image preloading",
        html_url="https://github.com/vercel/next.js/pull/55102",
        state="open",
        status="OPEN",
        is_draft=False,
        author_username="frontend_dev_student",
        author_github_id=student_a.github_user_id,
        created_at_github=today_noon,
        updated_at_github=today_noon,
        closed_at=None,
        merged_at=None,
        base_branch="canary",
        head_branch="optimize-images",
        commits=1,
        additions=65,
        deletions=4,
        changed_files=2,
        comments=2,
        review_comments=1,
        last_checked_at=now
    )

    # PR 3 (Historic): Created 5 days ago, repo facebook/react
    pr_a3_old = PullRequest(
        github_id=703,
        github_node_id="PR_NODE_703",
        student_id=student_a.id,
        repository_full_name="facebook/react",
        repository_owner="facebook",
        repository_name="react",
        organization_name="facebook",
        pr_number=27990,
        title="Documentation typo fix",
        html_url="https://github.com/facebook/react/pull/27990",
        state="closed",
        status="MERGED",
        is_draft=False,
        author_username="frontend_dev_student",
        author_github_id=student_a.github_user_id,
        created_at_github=five_days_ago,
        merged_at=five_days_ago,
        commits=1,
        additions=2,
        deletions=2,
        changed_files=1,
        last_checked_at=now
    )

    # PR 4: Student B created TODAY: CLOSED_UNMERGED, repo fastapi/fastapi, org fastapi
    pr_b1_today = PullRequest(
        github_id=704,
        github_node_id="PR_NODE_704",
        student_id=student_b.id,
        repository_full_name="fastapi/fastapi",
        repository_owner="fastapi",
        repository_name="fastapi",
        organization_name="fastapi",
        pr_number=9901,
        title="Prototype alternate schema resolver",
        html_url="https://github.com/fastapi/fastapi/pull/9901",
        state="closed",
        status="CLOSED_UNMERGED",
        is_draft=False,
        author_username="backend_dev_student",
        author_github_id=student_b.github_user_id,
        created_at_github=today_afternoon,
        closed_at=today_afternoon,
        merged_at=None,
        base_branch="master",
        head_branch="prototype-resolver",
        commits=2,
        additions=88,
        deletions=40,
        changed_files=3,
        comments=4,
        review_comments=2,
        last_checked_at=now
    )

    db_session.add_all([pr_a1_today, pr_a2_today, pr_a3_old, pr_b1_today])
    db_session.commit()

    # 3. VERIFY: "see how many Pull Requests each account has created today"
    students_res = client.get("/api/students")
    assert students_res.status_code == 200
    all_students = {s["github_username"]: s for s in students_res.json()}

    # Verify Student A (Alex)
    assert "frontend_dev_student" in all_students
    student_a_metrics = all_students["frontend_dev_student"]
    assert student_a_metrics["prs_today"] == 2
    assert student_a_metrics["merged_today"] == 1
    assert student_a_metrics["open_today"] == 1
    assert student_a_metrics["closed_unmerged_today"] == 0
    assert student_a_metrics["total_prs"] == 3  # 2 today + 1 five days ago

    # Verify Student B (Jordan)
    assert "backend_dev_student" in all_students
    student_b_metrics = all_students["backend_dev_student"]
    assert student_b_metrics["prs_today"] == 1
    assert student_b_metrics["merged_today"] == 0
    assert student_b_metrics["open_today"] == 0
    assert student_b_metrics["closed_unmerged_today"] == 1
    assert student_b_metrics["total_prs"] == 1

    # 4. VERIFY: "the status of each PR (merged, open, or closed), which organizations and repositories those PRs were submitted to, and all other relevant details"
    today_prs_res = client.get("/api/pull-requests?date_range=today")
    assert today_prs_res.status_code == 200
    today_prs_data = today_prs_res.json()
    today_prs = today_prs_data["items"]

    # Filter to only the PRs created today in this test
    test_pr_ids = {701, 702, 704}
    matched_today_prs = [p for p in today_prs if p["github_id"] in test_pr_ids]
    assert len(matched_today_prs) == 3

    # Inspect PR #28001
    react_pr = next(p for p in matched_today_prs if p["pr_number"] == 28001)
    assert react_pr["author_username"] == "frontend_dev_student"
    assert react_pr["status"] == "MERGED"
    assert react_pr["repository_full_name"] == "facebook/react"
    assert react_pr["repository_owner"] == "facebook"
    assert react_pr["repository_name"] == "react"
    assert react_pr["organization_name"] == "facebook"
    assert react_pr["title"] == "Fix Suspense boundary re-render loop"
    assert react_pr["html_url"] == "https://github.com/facebook/react/pull/28001"
    assert react_pr["commits"] == 3
    assert react_pr["additions"] == 142
    assert react_pr["deletions"] == 18
    assert react_pr["changed_files"] == 4
    assert react_pr["merged_by"] == "gaearon"
    assert react_pr["merged_at"] is not None

    # Inspect PR #55102
    next_pr = next(p for p in matched_today_prs if p["pr_number"] == 55102)
    assert next_pr["author_username"] == "frontend_dev_student"
    assert next_pr["status"] == "OPEN"
    assert next_pr["repository_full_name"] == "vercel/next.js"
    assert next_pr["organization_name"] == "vercel"
    assert next_pr["title"] == "Optimize app router image preloading"
    assert next_pr["additions"] == 65
    assert next_pr["merged_at"] is None

    # Inspect PR #9901
    fastapi_pr = next(p for p in matched_today_prs if p["pr_number"] == 9901)
    assert fastapi_pr["author_username"] == "backend_dev_student"
    assert fastapi_pr["status"] == "CLOSED_UNMERGED"
    assert fastapi_pr["repository_full_name"] == "fastapi/fastapi"
    assert fastapi_pr["organization_name"] == "fastapi"
    assert fastapi_pr["title"] == "Prototype alternate schema resolver"
    assert fastapi_pr["state"] == "closed"
    assert fastapi_pr["merged_at"] is None

    # 5. VERIFY: Dashboard summary for "today"
    dash_today_res = client.get("/api/dashboard/summary?date_range=today")
    assert dash_today_res.status_code == 200
    summary_today = dash_today_res.json()
    assert summary_today["total_prs"] >= 3
    assert summary_today["merged_prs"] >= 1
    assert summary_today["open_prs"] >= 1
    assert summary_today["closed_unmerged_prs"] >= 1
