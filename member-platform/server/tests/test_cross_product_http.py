import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import build_opener, ProxyHandler, Request

import pytest


ROOT = Path(__file__).resolve().parents[3]
ADMIN_ID = "09990000"
MEMBER_ID = "09990001"
OS_ENV_KEYS = {
    "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "SYSTEMDRIVE",
    "TEMP", "TMP", "APPDATA", "USERPROFILE",
}


def isolated_environment(server, data, settings):
    env = {key: value for key, value in os.environ.items() if key.upper() in OS_ENV_KEYS}
    env.update({
        "PYTHONPATH": str(server),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
    })
    env.update(settings)
    assert Path(env["PYTHONPATH"]) == server
    assert data.is_absolute()
    return env


class LiveService:
    def __init__(self, server, data, settings):
        self.server = server
        self.database = data / "service.db"
        self.env = isolated_environment(server, data, settings)
        self.process = None
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.opener = build_opener(ProxyHandler({}))

    def call(self, method, path, token=None, body=None, expected=200):
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + token
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(
            self.base + path,
            data=None if body is None else json.dumps(body).encode(),
            headers=headers,
            method=method,
        )
        try:
            response = self.opener.open(request, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            status = response.status
            payload = json.loads(response.read())
        allowed = (expected,) if isinstance(expected, int) else expected
        assert status in allowed, (method, path, status, payload)
        return payload

    def start(self):
        assert self.process is None or self.process.poll() is not None
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(self.port), "--no-proxy-headers", "--no-access-log",
             "--log-level", "warning"],
            cwd=self.server, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8",
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                output, _ = self.process.communicate(timeout=5)
                pytest.fail(f"{self.server} exited before readiness: {output}")
            try:
                assert self.call("GET", "/api/health")["ok"] is True
                return
            except (URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        self.stop()
        pytest.fail(f"{self.server} did not become healthy")

    def stop(self):
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.communicate(timeout=5)

    def assert_running(self):
        assert self.process is not None and self.process.poll() is None
        assert self.call("GET", "/api/health")["ok"] is True

    def assert_stopped(self):
        assert self.process is not None and self.process.poll() is not None
        with pytest.raises(OSError):
            with socket.create_connection(("127.0.0.1", self.port), timeout=1):
                pass


@pytest.fixture
def separate_products(tmp_path):
    exam_data = tmp_path / "exam"
    member_data = tmp_path / "member"
    exam_key, member_key = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
    exam = LiveService(ROOT / "server", exam_data, {
        "ALE_THIC_DATA_DIR": str(exam_data),
        "ALE_THIC_DB_PATH": str(exam_data / "service.db"),
        "ALE_THIC_ROLE": "authoritative",
        "SECRET_KEY": exam_key,
        "ADMIN_USERNAME": ADMIN_ID,
        "PUBLIC_PREFIX": "",
        "ADMIN_PUBLIC_PATH": "",
        "ARCHIVE_ENABLED": "0",
        "ALE_THIC_CAPTCHA_ENABLED": "0",
    })
    member = LiveService(ROOT / "member-platform" / "server", member_data, {
        "MEMBER_PLATFORM_DATA_DIR": str(member_data),
        "MEMBER_PLATFORM_DB_PATH": str(member_data / "service.db"),
        "MEMBER_PLATFORM_ROLE": "authoritative",
        "MEMBER_PLATFORM_SECRET_KEY": member_key,
        "MEMBER_PLATFORM_PUBLIC_PREFIX": "",
    })
    assert exam.database != member.database
    assert exam_key != member_key
    assert not any(key.startswith("MEMBER_PLATFORM_") for key in exam.env)
    assert not any(key.startswith("ALE_THIC_") for key in member.env)
    assert "SECRET_KEY" not in member.env
    initial_password = secrets.token_urlsafe(24)
    setup = subprocess.run(
        [sys.executable, "-c", "import json,sys; from scripts.bootstrap_member import bootstrap; "
         "bootstrap(*json.load(sys.stdin))"],
        input=json.dumps([ADMIN_ID, initial_password]), cwd=member.server, env=member.env,
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert setup.returncode == 0, setup.stdout + setup.stderr
    try:
        exam.start()
        member.start()
        assert exam.process.pid != member.process.pid
        yield exam, member, initial_password
    finally:
        member.stop()
        exam.stop()


def client_hash(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 100_000, 32,
    ).hex()


def login(service, student_id, password, role, changed):
    salt = service.call("GET", "/api/auth/salt?student_id=" + student_id)["salt"]
    account = service.call("POST", "/api/auth/login", body={
        "student_id": student_id, "client_hash": client_hash(password, salt),
    })
    assert account["student_id"] == student_id
    assert account["role"] == role
    assert account["pw_changed"] is changed
    assert account["token"]
    return account["token"]


def change_password(service, student_id, token, old_password, new_password):
    salt = service.call("GET", "/api/auth/salt?student_id=" + student_id)["salt"]
    new_salt = secrets.token_hex(16)
    assert service.call("POST", "/api/auth/change_password", token, {
        "old_client_hash": client_hash(old_password, salt),
        "new_salt": new_salt,
        "new_client_hash": client_hash(new_password, new_salt),
    })["ok"] is True


def assert_account(service, token, student_id, role):
    account = service.call("GET", "/api/auth/me", token)
    assert account["student_id"] == student_id
    assert account["role"] == role
    assert account["pw_changed"] is True


def assert_organization(member, token, role):
    identity = member.call("GET", "/api/v1/me", token)
    assert identity["role"] == role
    assert identity["auth_type"] == "web"
    assert identity["member_status"] == "active"
    assert identity["principal_id"]
    assert "profile:read:self" in identity["scopes"]


def test_cross_product_real_http_sessions_and_independent_lifecycles(separate_products):
    exam, member, initial_password = separate_products
    exam.assert_running()
    member.assert_running()
    assert member.call("GET", "/api/health")["service"] == "member-platform"
    assert exam.call("GET", "/openapi.json")["info"]["title"] == "Alethic Insight 招新平台"
    assert member.call("GET", "/openapi.json")["info"]["title"] == "Alethic Insight 内部成员服务"

    exam_token = login(exam, ADMIN_ID, ADMIN_ID, "admin", False)
    exam.call("GET", "/api/admin/accounts", exam_token, expected=403)
    exam_password = secrets.token_urlsafe(24)
    change_password(exam, ADMIN_ID, exam_token, ADMIN_ID, exam_password)
    exam_token = login(exam, ADMIN_ID, exam_password, "admin", True)

    admin_token = login(member, ADMIN_ID, initial_password, "admin", False)
    member.call("GET", "/api/v1/me", admin_token, expected=403)
    member.call("GET", "/api/admin/accounts", admin_token, expected=403)
    admin_password = secrets.token_urlsafe(24)
    change_password(member, ADMIN_ID, admin_token, initial_password, admin_password)
    admin_token = login(member, ADMIN_ID, admin_password, "admin", True)
    created = member.call("POST", "/api/admin/accounts", admin_token, {
        "student_id": MEMBER_ID, "nickname": "Synthetic HTTP member",
    }, expected=201)
    member_token = login(member, MEMBER_ID, created["temporary_password"], "member", False)
    member.call("GET", "/api/v1/me", member_token, expected=403)
    member_password = secrets.token_urlsafe(24)
    change_password(member, MEMBER_ID, member_token, created["temporary_password"], member_password)
    member_token = login(member, MEMBER_ID, member_password, "member", True)

    exam.assert_running()
    member.assert_running()
    assert_account(exam, exam_token, ADMIN_ID, "admin")
    for token, student_id, role in ((admin_token, ADMIN_ID, "admin"), (member_token, MEMBER_ID, "member")):
        assert_account(member, token, student_id, role)
        assert_organization(member, token, role)
        for path in ("/api/auth/me", "/api/admin/accounts"):
            exam.call("GET", path, token, expected=(401, 403))
    for path in ("/api/auth/me", "/api/admin/accounts", "/api/v1/me", "/api/v1/projects"):
        member.call("GET", path, exam_token, expected=(401, 403))
    member.call("GET", "/api/admin/accounts", member_token, expected=(401, 403))
    assert {row["student_id"] for row in member.call("GET", "/api/admin/accounts", admin_token)["items"]} == {ADMIN_ID, MEMBER_ID}
    assert [row["student_id"] for row in exam.call("GET", "/api/admin/accounts", exam_token)["items"]] == [ADMIN_ID]
    assert member.call("GET", "/api/v1/projects", member_token)["items"] == []
    assert exam.call("GET", "/api/campaigns", exam_token) == []

    paths = exam.call("GET", "/openapi.json")["paths"]
    assert not any(path == "/api/v1" or path.startswith("/api/v1/") for path in paths)
    for path in ("/api/v1", "/api/v1/", "/api/v1/me", "/api/v1/projects",
                 "/api/v1/auth/cli/token", "/api/v1/applications/drafts"):
        for method in ("GET", "POST", "DELETE"):
            exam.call(method, path, exam_token, expected=404)
    for path in ("/api/campaigns", "/api/exam"):
        member.call("GET", path, admin_token, expected=404)

    with sqlite3.connect(exam.database) as conn:
        exam_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    with sqlite3.connect(member.database) as conn:
        member_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert conn.execute("PRAGMA application_id").fetchone()[0] == 0x4D454D42
    assert {"campaign", "application", "exam_session"} <= exam_tables
    assert not any(table.startswith("org_") or table == "service_request" for table in exam_tables)
    assert {"org_principal", "org_project", "service_request"} <= member_tables
    assert not {"campaign", "application", "exam_session"} & member_tables

    exam.stop()
    exam.assert_stopped()
    member.assert_running()
    assert_account(member, member_token, MEMBER_ID, "member")
    assert_organization(member, member_token, "member")
    assert_organization(member, admin_token, "admin")
    assert member.call("GET", "/api/v1/projects", member_token)["items"] == []

    exam.start()
    exam.assert_running()
    member.assert_running()
    exam_token = login(exam, ADMIN_ID, exam_password, "admin", True)
    assert_account(exam, exam_token, ADMIN_ID, "admin")
    assert_organization(member, member_token, "member")
    member.stop()
    member.assert_stopped()
    exam.assert_running()
    assert_account(exam, exam_token, ADMIN_ID, "admin")
    assert [row["student_id"] for row in exam.call("GET", "/api/admin/accounts", exam_token)["items"]] == [ADMIN_ID]
