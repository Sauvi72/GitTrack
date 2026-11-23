import pytest


def test_scopes_crud(client):
    # 1. Get scopes (global scope is initialized)
    res = client.get("/api/scopes")
    assert res.status_code == 200
    scopes = res.json()
    assert any(s["scope_type"] == "global" for s in scopes)

    # 2. Create organization scope
    res_org = client.post("/api/scopes", json={
        "scope_type": "organization",
        "scope_value": "tensorflow",
        "display_name": "TensorFlow Org"
    })
    assert res_org.status_code == 201
    org_id = res_org.json()["id"]
    assert res_org.json()["scope_value"] == "tensorflow"

    # 3. Create repository scope
    res_repo = client.post("/api/scopes", json={
        "scope_type": "repository",
        "scope_value": "pytorch/pytorch",
        "display_name": "PyTorch Core"
    })
    assert res_repo.status_code == 201
    repo_id = res_repo.json()["id"]

    # 4. Reject invalid repository scope format (missing slash)
    res_bad_repo = client.post("/api/scopes", json={
        "scope_type": "repository",
        "scope_value": "invalid-repo-without-slash"
    })
    assert res_bad_repo.status_code == 400

    # 5. Toggle active status
    res_toggle = client.patch(f"/api/scopes/{org_id}", json={"is_active": False})
    assert res_toggle.status_code == 200
    assert res_toggle.json()["is_active"] is False

    # 6. Delete scope
    res_del = client.delete(f"/api/scopes/{repo_id}")
    assert res_del.status_code == 200

    # 7. Disallow deleting global scope
    global_scope = next(s for s in client.get("/api/scopes").json() if s["scope_type"] == "global")
    res_del_global = client.delete(f"/api/scopes/{global_scope['id']}")
    assert res_del_global.status_code == 400
