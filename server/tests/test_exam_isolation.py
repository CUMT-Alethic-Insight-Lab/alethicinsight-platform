import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import auth, config, db
from app.main import app


SERVER = Path(__file__).resolve().parents[1]
LEGACY_TABLES = (
    "org_principal", "org_cli_grant", "org_cli_authorization", "org_project",
    "org_document", "org_confirmation", "org_idempotency", "service_request",
    "service_request_review",
)


@pytest.mark.parametrize("role", ["authoritative", "edge"])
def test_fresh_exam_process_has_no_member_runtime(tmp_path, role):
    env = os.environ.copy()
    env.update({
        "ALE_THIC_ROLE": role,
        "ALE_THIC_DATA_DIR": str(tmp_path / "data"),
        "ALE_THIC_DB_PATH": str(tmp_path / "exam.db"),
        "SECRET_KEY": "isolation-test-secret",
        "STAGING_SECRET": "",
        "ARCHIVE_ENABLED": "0",
    })
    result = subprocess.run(
        [sys.executable, "-c", '''
import sys
from fastapi.testclient import TestClient
from app import auth, config, db
from app.main import app

with TestClient(app) as client:
    assert client.get('/api/health').json()['ok'] is True
    salt = client.get('/api/auth/salt', params={'student_id': config.ADMIN_USERNAME}).json()['salt']
    login = client.post('/api/auth/login', json={
        'student_id': config.ADMIN_USERNAME,
        'client_hash': auth.compute_client_hash(config.ADMIN_USERNAME, salt),
    })
    assert login.status_code == 200, login.text
    headers = {'Authorization': 'Bearer ' + login.json()['token']}
    for path in ['/api/v1', '/api/v1/', '/api/v1/me', '/api/v1/projects',
                 '/api/v1/capabilities', '/api/v1/auth/cli/token', '/api/v1/applications/drafts',
                 '/org', '/static/org.html', '/static/org.js', '/static/css/org.css']:
        for method in ['GET', 'POST', 'DELETE']:
            response = client.request(method, path, headers=headers, follow_redirects=False)
            assert response.status_code in (404, 405), (method, path, response.text)
            assert 'location' not in response.headers
    paths = client.get('/openapi.json').json()['paths']
    assert not any(path == '/api/v1' or path.startswith('/api/v1/') for path in paths)
    assert ('/api/internal/ingest-staged' in paths) == (not config.IS_EDGE)
    with db.connection() as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {
        'membership', 'campaign', 'application', 'question', 'exam_session', 'exam_score',
        'interview_score', 'admin_user', 'account', 'login_session', 'login_attempt',
        'captcha', 'interview_slot', 'audit_log', 'sqlite_sequence',
    }, tables
    assert not any(name.startswith('app.org_') or name.startswith('app.routes.org_')
                   or name == 'app.service_requests' for name in sys.modules)
'''],
        cwd=SERVER, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def legacy_snapshot():
    with db.connection() as conn:
        return {
            table: (
                conn.execute("SELECT sql FROM sqlite_master WHERE name = ?", (table,)).fetchone()[0],
                [tuple(row) for row in conn.execute(f"SELECT * FROM {table}")],
            )
            for table in LEGACY_TABLES
        }


@pytest.mark.parametrize("operation", ["change_password", "reset_password", "role"])
def test_exam_account_lifecycle_never_mutates_legacy_member_data(tmp_path, monkeypatch, operation):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "legacy.db")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "ARCHIVE_ENABLED", False)
    db.init_db()
    student_id = "09990001"
    password = "Exam#isolation-1"
    salt = auth.new_salt()
    client_hash = auth.compute_client_hash(password, salt)
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO account (student_id, role, pw_salt, pw_hash, pw_changed, created_at, updated_at)"
            " VALUES (?, 'member', ?, ?, 1, 'now', 'now')",
            (student_id, salt, auth.store_hash(client_hash)),
        )
        conn.execute(
            "INSERT INTO membership (student_id, name, source, created_at) VALUES (?, '历史考生', 'test', 'now')",
            (student_id,),
        )
        for table in LEGACY_TABLES:
            conn.execute(f"CREATE TABLE {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            conn.execute(f"INSERT INTO {table} VALUES ('historical', 'must remain untouched')")
    before = legacy_snapshot()
    with TestClient(app) as client:
        login = client.post('/api/auth/login', json={'student_id': student_id, 'client_hash': client_hash})
        assert login.status_code == 200, login.text
        assert login.json()['role'] == 'member'
        assert login.json()['name'] == '历史考生'
        member_headers = {'Authorization': 'Bearer ' + login.json()['token']}
        assert client.get('/api/auth/me', headers=member_headers).status_code == 200
        if operation == 'change_password':
            new_salt = auth.new_salt()
            response = client.post('/api/auth/change_password', headers=member_headers, json={
                'old_client_hash': client_hash,
                'new_salt': new_salt,
                'new_client_hash': auth.compute_client_hash('Exam#isolation-2', new_salt),
            })
            assert response.status_code == 200, response.text
        else:
            with db.connection() as conn:
                conn.execute('UPDATE account SET pw_changed = 1 WHERE student_id = ?', (config.ADMIN_USERNAME,))
                token = auth.issue_session(conn, 'admin', None, config.ADMIN_USERNAME)
            response = client.post(
                f'/api/admin/accounts/{student_id}/{operation}',
                headers={'Authorization': 'Bearer ' + token},
                json={'role': 'applicant'} if operation == 'role' else {},
            )
            assert response.status_code == 200, response.text
            assert client.get('/api/auth/me', headers=member_headers).status_code == 401
        assert legacy_snapshot() == before
        with db.connection() as conn:
            assert conn.execute('SELECT name FROM membership WHERE student_id = ?', (student_id,)).fetchone()[0] == '历史考生'
    db.init_db()
    assert legacy_snapshot() == before
