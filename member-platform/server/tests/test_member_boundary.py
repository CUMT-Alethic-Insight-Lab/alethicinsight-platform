import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from app import auth, config, db
from app.main import app
from scripts.bootstrap_member import bootstrap

SERVER = Path(__file__).resolve().parents[1]


@pytest.fixture
def member_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "member.db")
    monkeypatch.setattr(config, "IS_EDGE", False)
    with TestClient(app) as client:
        yield client


def login(client, student_id, password):
    salt = client.get("/api/auth/salt", params={"student_id": student_id}).json()["salt"]
    return client.post("/api/auth/login", json={"student_id": student_id,
                       "client_hash": auth.compute_client_hash(password, salt)})


def change(client, student_id, password, new_password, headers):
    salt = client.get("/api/auth/salt", params={"student_id": student_id}).json()["salt"]
    new_salt = auth.new_salt()
    return client.post("/api/auth/change_password", headers=headers, json={
        "old_client_hash": auth.compute_client_hash(password, salt), "new_salt": new_salt,
        "new_client_hash": auth.compute_client_hash(new_password, new_salt),
    })


def headers(response):
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["token"]}


def grant(client, web):
    rid = secrets.token_urlsafe(24)
    result = client.post("/api/v1/auth/cli/authorization-requests", headers=web, json={"request_id": rid})
    assert result.status_code == 200, result.text
    return rid, result.json()["code"]


def test_explicit_bootstrap_login_management_and_revocation(member_client):
    client = member_client
    with db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM account").fetchone()[0] == 0
    password = "Separate#Bootstrap2026"
    bootstrap("local-owner", password)
    with pytest.raises(RuntimeError, match="empty member"):
        bootstrap("another-owner", password)
    admin_login = login(client, "local-owner", password)
    admin = headers(admin_login)
    assert admin_login.json()["pw_changed"] is False
    assert client.get("/api/admin/accounts", headers=admin).status_code == 403
    assert client.get("/api/v1/me", headers=admin).status_code == 403
    assert change(client, "local-owner", password, "Changed#Owner2026", admin).status_code == 200
    created = client.post("/api/admin/accounts", headers=admin, json={"student_id": "member-one", "nickname": "Local Member"})
    assert created.status_code == 201, created.text
    assert created.headers["cache-control"] == "no-store"
    temp = created.json()["temporary_password"]
    assert temp != "member-one"
    web = headers(login(client, "member-one", temp))
    assert client.get("/api/v1/me", headers=web).status_code == 403
    assert change(client, "member-one", temp, "Changed#Member2026", web).status_code == 200
    assert client.get("/api/v1/me", headers=web).status_code == 200
    rid, code = grant(client, web)
    cli = headers(client.post("/api/v1/auth/cli/token", json={"request_id": rid, "code": code}))
    pending_id, pending_code = grant(client, web)
    other_session = headers(login(client, "member-one", "Changed#Member2026"))
    assert change(client, "member-one", "Changed#Member2026", "Rotated#Member2026", web).status_code == 200
    assert client.get("/api/auth/me", headers=other_session).status_code == 401
    assert client.get("/api/v1/me", headers=cli).status_code == 401
    assert client.post("/api/v1/auth/cli/token", json={"request_id": pending_id, "code": pending_code}).status_code == 401
    rid, code = grant(client, web)
    cli = headers(client.post("/api/v1/auth/cli/token", json={"request_id": rid, "code": code}))
    pending_id, pending_code = grant(client, web)
    reset = client.post("/api/admin/accounts/member-one/reset_password", headers=admin)
    assert reset.status_code == 200
    assert reset.json()["temporary_password"] not in ("member-one", temp)
    assert client.get("/api/auth/me", headers=web).status_code == 401
    assert client.get("/api/v1/me", headers=cli).status_code == 401
    assert client.post("/api/v1/auth/cli/token", json={"request_id": pending_id, "code": pending_code}).status_code == 401
    assert login(client, "member-one", "Rotated#Member2026").status_code == 401
    reset_web = headers(login(client, "member-one", reset.json()["temporary_password"]))
    assert client.get("/api/v1/me", headers=reset_web).status_code == 403
    assert client.post("/api/admin/accounts/member-one/role", headers=admin, json={"role": "inactive"}).status_code == 200
    assert client.get("/api/auth/me", headers=reset_web).status_code == 401
    assert login(client, "member-one", reset.json()["temporary_password"]).status_code == 401
    assert client.post("/api/admin/accounts/local-owner/role", headers=admin, json={"role": "member"}).status_code == 400
    assert client.post("/api/auth/logout", headers=admin).status_code == 200
    assert client.get("/api/auth/me", headers=admin).status_code == 401
    with db.connection() as conn:
        raw = str([dict(row) for row in conn.execute("SELECT * FROM account")])
        assert password not in raw and temp not in raw and "Changed#Member2026" not in raw
        assert len(conn.execute("SELECT pw_hash FROM account LIMIT 1").fetchone()[0]) == 64


def database_state(path):
    with sqlite3.connect(path) as conn:
        schema = conn.execute("SELECT type, name, tbl_name, rootpage, sql FROM sqlite_master ORDER BY type, name").fetchall()
        identity = conn.execute("PRAGMA application_id").fetchone()[0]
    return path.read_bytes(), schema, identity


@pytest.mark.parametrize("table", ["campaign", "application", "question", "exam_session", "exam_score", "interview_score", "interview_slot", "admin_user", "unrelated", "sqliteXexternal"])
def test_refuse_exam_or_unknown_database_without_mutation(tmp_path, monkeypatch, table):
    path = tmp_path / "foreign.db"
    with sqlite3.connect(path) as conn:
        conn.execute(f"CREATE TABLE {table} (id TEXT)")
        conn.execute(f"INSERT INTO {table} VALUES ('untouched')")
    before = database_state(path)
    monkeypatch.setattr(config, "DB_PATH", path)
    with pytest.raises(RuntimeError, match="Refusing"):
        db.init_db()
    assert database_state(path) == before


@pytest.mark.parametrize("schema", [
    "CREATE VIEW external_accounts AS SELECT 'foreign' AS student_id;",
    "CREATE VIEW sqliteXexternal AS SELECT 'foreign' AS student_id;",
    "CREATE TABLE account (student_id TEXT); CREATE INDEX member_lookup ON account(student_id);",
    "CREATE TABLE account (student_id TEXT); CREATE TRIGGER member_insert AFTER INSERT ON account BEGIN SELECT 1; END;",
], ids=["view-only", "sqlite-like-view", "index", "trigger"])
def test_refuse_unmarked_user_schema_without_mutation(tmp_path, monkeypatch, schema):
    path = tmp_path / "unmarked.db"
    with sqlite3.connect(path) as conn:
        conn.executescript(schema)
    before = database_state(path)
    assert before[2] == 0
    monkeypatch.setattr(config, "DB_PATH", path)
    with pytest.raises(RuntimeError, match="unmarked"):
        db.init_db()
    assert database_state(path) == before


def test_marked_member_database_preserves_user_indexes(member_client):
    with db.connection() as conn:
        conn.execute("CREATE INDEX member_role_lookup ON account(role)")
        conn.execute("CREATE UNIQUE INDEX sqliteXmember_lookup ON account(student_id)")
        conn.execute("INSERT INTO account (student_id, created_at, updated_at) VALUES ('indexed-member', '', '')")
    before = database_state(config.DB_PATH)
    db.init_db()
    with db.connection() as conn:
        assert conn.execute("SELECT student_id FROM account INDEXED BY member_role_lookup WHERE role='member'").fetchone()[0] == "indexed-member"
        assert conn.execute("SELECT student_id FROM account INDEXED BY sqliteXmember_lookup WHERE student_id='indexed-member'").fetchone()[0] == "indexed-member"
    assert database_state(config.DB_PATH)[1:] == before[1:]


def test_refuse_unmarked_account_database_and_wrong_identity(tmp_path, monkeypatch):
    path = tmp_path / "account.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE account (student_id TEXT)")
    monkeypatch.setattr(config, "DB_PATH", path)
    before = database_state(path)
    with pytest.raises(RuntimeError, match="unmarked"):
        db.init_db()
    assert database_state(path) == before
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA application_id=123")
    before = database_state(path)
    with pytest.raises(RuntimeError, match="identity"):
        db.init_db()
    assert database_state(path) == before


def test_only_member_tables_no_exam_routes_no_exam_lifecycle(member_client):
    with db.connection() as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND substr(name, 1, 7) != 'sqlite_'")}
        assert tables == db.ALLOWED_TABLES
        assert conn.execute("PRAGMA application_id").fetchone()[0] == db.APPLICATION_ID
        assert "campaign_id" not in {r[1] for r in conn.execute("PRAGMA table_info(login_session)")}
    for path in ("/api/campaigns", "/api/campaigns/latest-open", "/api/campaigns/2026/auth/login", "/api/exam", "/api/internal", "/admin", "/apply/2026"):
        assert member_client.get(path).status_code == 404
    assert not any(name in sys.modules for name in ("app.archive", "app.maintenance", "app.staging", "app.routes.exam", "app.routes.campaigns"))
    assert not hasattr(auth, "require_applicant")


def test_database_switch_does_not_share_sessions(member_client, tmp_path, monkeypatch):
    first = config.DB_PATH
    bootstrap("local-owner", "Separate#Bootstrap2026")
    web = headers(login(member_client, "local-owner", "Separate#Bootstrap2026"))
    assert change(member_client, "local-owner", "Separate#Bootstrap2026", "Changed#Owner2026", web).status_code == 200
    rid, code = grant(member_client, web)
    cli = headers(member_client.post("/api/v1/auth/cli/token", json={"request_id": rid, "code": code}))
    second = tmp_path / "second.db"
    monkeypatch.setattr(config, "DB_PATH", second)
    bootstrap("local-owner", "Separate#Bootstrap2026")
    assert member_client.get("/api/auth/me", headers=web).status_code == 401
    assert member_client.get("/api/v1/me", headers=cli).status_code == 401
    monkeypatch.setattr(config, "DB_PATH", first)
    assert member_client.get("/api/auth/me", headers=web).status_code == 200


def test_rate_limits_account_and_ip_not_spoofable_by_headers(member_client):
    bootstrap("local-owner", "Separate#Bootstrap2026")
    for _ in range(auth.LOGIN_FAIL_LIMIT):
        assert member_client.post("/api/auth/login", json={"student_id": "local-owner", "client_hash": "0" * 64}).status_code == 401
    assert member_client.post("/api/auth/login", json={"student_id": "local-owner", "client_hash": "0" * 64}).status_code == 429
    assert member_client.get("/api/auth/salt", params={"student_id": "local-owner"}).status_code == 429
    assert member_client.get("/api/auth/salt", params={"student_id": "other"}, headers={"X-Forwarded-For": "127.0.0.99"}).status_code == 429


def test_environment_is_namespaced_and_shared_secret_db_rejected(tmp_path, monkeypatch):
    env = dict(os.environ)
    env.pop("MEMBER_PLATFORM_SECRET_KEY", None)
    env.update({"SECRET_KEY": "exam-key-not-usable", "MEMBER_PLATFORM_DB_PATH": str(tmp_path / "new.db")})
    result = subprocess.run([sys.executable, "-c", "from app import db; db.init_db()"], cwd=SERVER, env=env, capture_output=True, text=True)
    assert result.returncode != 0 and "MEMBER_PLATFORM_SECRET_KEY" in result.stderr
    assert not (tmp_path / "new.db").exists()
    monkeypatch.setenv("SECRET_KEY", config.SECRET_KEY)
    with pytest.raises(RuntimeError, match="never reuse"):
        config.validate()
    monkeypatch.setenv("SECRET_KEY", "different-exam-key")
    monkeypatch.setenv("ALE_THIC_DB_PATH", str(config.DB_PATH))
    with pytest.raises(RuntimeError, match="must not reuse"):
        config.validate()


def test_pages_have_member_only_session_and_login_entry(member_client):
    page = member_client.get("/login")
    assert page.status_code == 200 and '/static/login.js' in page.text
    js = member_client.get("/static/login.js").text
    org_js = member_client.get("/static/org.js").text
    for script in (js, org_js):
        assert "member_platform_session_v1" in script
        for old in ("alethic_admin_token", "alethic_session", "aletnic_admin_token"):
            assert old not in script
    assert "localStorage.setItem" not in org_js
    assert "'auth/login'" in js and "'auth/change_password'" in js
    assert "window.confirm" in js and "textContent" in js
    assert 'unsafe-inline' not in page.text and "innerHTML" not in js


def test_public_prefix_for_both_pages(member_client, monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_PREFIX", "/members")
    for route, script in (("/login", "login.js"), ("/org", "org.js")):
        page = member_client.get(route)
        assert '/members/static/' + script in page.text
        assert 'data-prefix="/members"' in page.text
        assert '__PREFIX__' not in page.text
