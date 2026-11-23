import pytest


def test_auth_login_success(client):
    res = client.post("/api/auth/login", json={
        "email": "test_teacher@opentrack.edu",
        "password": "TestPass123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "access_token" in res.cookies

    # Test /api/auth/me with Bearer token header
    token = data["access_token"]
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    me = res_me.json()
    assert me["email"] == "test_teacher@opentrack.edu"
    assert me["full_name"] == "Dr. Test Teacher"


def test_auth_login_invalid_password(client):
    res = client.post("/api/auth/login", json={
        "email": "test_teacher@opentrack.edu",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401


def test_auth_me_unauthorized(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_auth_logout(client):
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
