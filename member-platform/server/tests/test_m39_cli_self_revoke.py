import secrets

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import auth, config, db, org_errors
from app.org_auth import digest
from app.routes import org_auth, org_meta


SELF_REVOKE = "/api/v1/auth/cli/grants/self"


@pytest.fixture
def self_revoke_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "self-revoke.db")
    monkeypatch.setattr(config, "IS_EDGE", False)
    db.init_db()
    app = FastAPI()
    app.include_router(org_auth.router)
    app.include_router(org_meta.router)
    org_errors.install_org_error_handlers(app)
    with TestClient(app) as client:
        yield client


def web_session(student_id):
    now = auth._utcnow().isoformat()
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO account (student_id, role, pw_hash, pw_changed, created_at, updated_at)"
            " VALUES (?, 'member', 'test-password', 1, ?, ?)",
            (student_id, now, now),
        )
        token = auth.issue_session(conn, "member", None, student_id)
    return {"Authorization": "Bearer " + token}


def cli_grant(client, web):
    request_id = secrets.token_urlsafe(24)
    response = client.post(
        "/api/v1/auth/cli/authorization-requests", headers=web,
        json={"request_id": request_id, "scopes": ["profile:read:self"]},
    )
    assert response.status_code == 200, response.text
    response = client.post(
        "/api/v1/auth/cli/token",
        json={"request_id": request_id, "code": response.json()["code"]},
    )
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    with db.connection() as conn:
        grant_id = conn.execute(
            "SELECT id FROM org_cli_grant WHERE token_hash = ?", (digest(token),),
        ).fetchone()["id"]
    return {"Authorization": "Bearer " + token}, grant_id


def revoked_at(grant_id):
    with db.connection() as conn:
        return conn.execute(
            "SELECT revoked_at FROM org_cli_grant WHERE id = ?", (grant_id,),
        ).fetchone()["revoked_at"]


def test_self_revoke_invalidates_old_token_and_retry_is_unauthorized(self_revoke_client):
    client = self_revoke_client
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    document = response.json()
    operation = document["paths"][SELF_REVOKE]["delete"]
    assert operation["security"] == [{"HTTPBearer": []}]
    assert document["components"]["securitySchemes"]["HTTPBearer"] == {
        "type": "http", "scheme": "bearer",
    }
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    model = document["components"]["schemas"][schema["$ref"].rsplit("/", 1)[1]]
    assert model["type"] == "object"
    assert model["required"] == ["revoked"]
    assert model["properties"]["revoked"]["type"] == "boolean"
    web = web_session("self-owner")
    cli, grant_id = cli_grant(client, web)
    assert client.get("/api/v1/me", headers=cli).status_code == 200
    response = client.delete(SELF_REVOKE, headers=cli)
    assert response.status_code == 200, response.text
    assert response.json() == {"revoked": True}
    assert response.headers["cache-control"] == "no-store"
    assert revoked_at(grant_id) is not None
    assert client.get("/api/v1/me", headers=cli).status_code == 401
    assert client.delete(SELF_REVOKE, headers=cli).status_code == 401
    assert client.get("/api/v1/me", headers=web).status_code == 200


def test_self_revoke_cannot_target_same_users_other_grant(self_revoke_client):
    client = self_revoke_client
    web = web_session("two-grants")
    first, first_id = cli_grant(client, web)
    second, second_id = cli_grant(client, web)
    response = client.delete(SELF_REVOKE, headers=first, params={"grant_id": second_id})
    assert response.status_code == 200
    assert response.json() == {"revoked": True}
    assert revoked_at(first_id) is not None
    assert revoked_at(second_id) is None
    assert client.get("/api/v1/me", headers=second).status_code == 200
    assert client.delete(f"/api/v1/auth/cli/grants/{second_id}", headers=second).status_code == 403
    assert client.delete(f"/api/v1/auth/cli/grants/{second_id}", headers=web).status_code == 200
    assert client.get("/api/v1/me", headers=second).status_code == 401


def test_web_session_cannot_impersonate_cli_self_revoke(self_revoke_client):
    client = self_revoke_client
    web = web_session("web-owner")
    cli, grant_id = cli_grant(client, web)
    response = client.delete(SELF_REVOKE, headers=web)
    assert response.status_code == 403, response.text
    assert revoked_at(grant_id) is None
    assert client.get("/api/v1/me", headers=cli).status_code == 200


def test_edge_refuses_self_and_web_id_revocation(self_revoke_client, monkeypatch):
    client = self_revoke_client
    web = web_session("edge-owner")
    cli, grant_id = cli_grant(client, web)
    monkeypatch.setattr(config, "IS_EDGE", True)
    for path, headers in [(SELF_REVOKE, cli), (f"/api/v1/auth/cli/grants/{grant_id}", web)]:
        response = client.delete(path, headers=headers)
        assert response.status_code == 503, response.text
        assert response.headers["retry-after"] == "60"
    assert revoked_at(grant_id) is None
    assert client.get("/api/v1/me", headers=cli).status_code == 200


def test_other_users_token_cannot_revoke_victims_grant(self_revoke_client):
    client = self_revoke_client
    victim_web = web_session("victim")
    victim_cli, victim_id = cli_grant(client, victim_web)
    other_web = web_session("other")
    other_cli, other_id = cli_grant(client, other_web)
    assert client.delete(SELF_REVOKE, headers=other_web, params={"grant_id": victim_id}).status_code == 403
    assert client.delete(f"/api/v1/auth/cli/grants/{victim_id}", headers=other_cli).status_code == 403
    assert client.delete(f"/api/v1/auth/cli/grants/{victim_id}", headers=other_web).status_code == 404
    response = client.delete(SELF_REVOKE, headers=other_cli, params={"grant_id": victim_id})
    assert response.status_code == 200, response.text
    assert response.json() == {"revoked": True}
    assert revoked_at(other_id) is not None
    assert revoked_at(victim_id) is None
    assert client.get("/api/v1/me", headers=victim_cli).status_code == 200


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-cli-token"}])
def test_missing_or_invalid_token_is_unauthorized(self_revoke_client, headers):
    assert self_revoke_client.delete(SELF_REVOKE, headers=headers).status_code == 401
