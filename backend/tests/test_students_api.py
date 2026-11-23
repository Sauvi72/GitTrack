import pytest
from app.services.github_client import GitHubClient, GitHubUserNotFoundError


def test_create_and_get_students(client, monkeypatch):
    # Mock GitHubClient.get_user
    def mock_get_user(self, username):
        if username == "octocat_student":
            return {
                "login": "octocat_student",
                "id": 112233,
                "html_url": "https://github.com/octocat_student",
                "name": "Octo Cat Jr."
            }
        raise GitHubUserNotFoundError(f"User {username} not found")

    monkeypatch.setattr(GitHubClient, "get_user", mock_get_user)

    # 1. Create student
    res = client.post("/api/students", json={
        "github_username": "octocat_student",
        "display_name": "Octo Custom"
    })
    assert res.status_code == 201
    created = res.json()
    assert created["github_username"] == "octocat_student"
    assert created["github_user_id"] == 112233
    assert created["display_name"] == "Octo Custom"
    assert created["is_active"] is True
    student_id = created["id"]

    # 2. Reject duplicate username
    res_dup = client.post("/api/students", json={"github_username": "OCTOCAT_STUDENT"})
    assert res_dup.status_code == 400

    # 3. Reject non-existent GitHub user
    res_404 = client.post("/api/students", json={"github_username": "ghost_nonexistent"})
    assert res_404.status_code == 404

    # 4. Get list of students
    res_list = client.get("/api/students")
    assert res_list.status_code == 200
    items = res_list.json()
    assert any(s["id"] == student_id for s in items)

    # 5. Search students
    res_search = client.get("/api/students?q=octo")
    assert res_search.status_code == 200
    assert len(res_search.json()) >= 1

    # 6. Get single student
    res_single = client.get(f"/api/students/{student_id}")
    assert res_single.status_code == 200
    assert res_single.json()["id"] == student_id

    # 7. Update student
    res_update = client.patch(f"/api/students/{student_id}", json={
        "display_name": "Updated Name"
    })
    assert res_update.status_code == 200
    assert res_update.json()["display_name"] == "Updated Name"

    # 8. Delete student permanently
    res_delete = client.delete(f"/api/students/{student_id}")
    assert res_delete.status_code == 200
    res_check = client.get(f"/api/students/{student_id}")
    assert res_check.status_code == 404
