import sqlite3
from contextlib import contextmanager

from . import config

APPLICATION_ID = 0x4D454D42
SCHEMA = """
CREATE TABLE IF NOT EXISTS account (
    student_id TEXT PRIMARY KEY, role TEXT NOT NULL DEFAULT 'member',
    nickname TEXT NOT NULL DEFAULT '', pw_salt TEXT, pw_hash TEXT,
    pw_changed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS login_session (
    token_hash TEXT PRIMARY KEY, kind TEXT NOT NULL, student_id TEXT,
    created_at TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS login_attempt (
    key TEXT PRIMARY KEY, fails INTEGER NOT NULL DEFAULT 0, window_start TEXT, locked_until TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL, action TEXT NOT NULL,
    target TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS org_principal (
    id TEXT PRIMARY KEY, student_id TEXT NOT NULL UNIQUE REFERENCES account(student_id), created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS org_cli_grant (
    id TEXT PRIMARY KEY, principal_id TEXT NOT NULL REFERENCES org_principal(id),
    token_hash TEXT NOT NULL UNIQUE, scopes_json TEXT NOT NULL, credential_hash TEXT NOT NULL,
    created_at TEXT NOT NULL, expires_at TEXT NOT NULL, revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS org_cli_authorization (
    request_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL REFERENCES org_principal(id),
    code_hash TEXT NOT NULL, scopes_json TEXT NOT NULL, credential_hash TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT
);
CREATE TABLE IF NOT EXISTS org_project (
    id TEXT PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
    description TEXT NOT NULL, lifecycle_status TEXT NOT NULL,
    visibility TEXT NOT NULL, owner_student_id TEXT, recruiting INTEGER NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS org_document (
    id TEXT PRIMARY KEY, source_repo TEXT NOT NULL, path TEXT NOT NULL,
    revision TEXT NOT NULL, visibility TEXT NOT NULL, source_url TEXT NOT NULL,
    title TEXT NOT NULL, content TEXT NOT NULL, indexed_at TEXT NOT NULL,
    updated_at TEXT NOT NULL, UNIQUE(source_repo, path)
);
CREATE TABLE IF NOT EXISTS service_request (
    id TEXT PRIMARY KEY, applicant_id TEXT NOT NULL, project_id TEXT,
    kind TEXT NOT NULL, form_revision TEXT NOT NULL, payload_json TEXT NOT NULL,
    status TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT NOT NULL,
    submitted_at TEXT, updated_at TEXT NOT NULL, reviewer_id TEXT, review_reason TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS service_request_review (
    id TEXT PRIMARY KEY, request_id TEXT NOT NULL, reviewer_id TEXT NOT NULL,
    decision TEXT NOT NULL, reason TEXT NOT NULL, decided_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS org_confirmation (
    token_hash TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
    principal_id TEXT NOT NULL, content_hash TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT
);
CREATE TABLE IF NOT EXISTS org_idempotency (
    principal_id TEXT NOT NULL, operation TEXT NOT NULL, key TEXT NOT NULL,
    request_hash TEXT NOT NULL, response_json TEXT NOT NULL, created_at TEXT NOT NULL,
    PRIMARY KEY(principal_id, operation, key)
);
"""
ALLOWED_TABLES = {
    'account', 'login_session', 'login_attempt', 'audit_log', 'org_principal',
    'org_cli_grant', 'org_cli_authorization', 'org_project', 'org_document',
    'service_request', 'service_request_review', 'org_confirmation', 'org_idempotency',
}


def _guard(conn, initializing=False):
    schema = conn.execute(
        "SELECT type, name FROM sqlite_master"
        " WHERE type IN ('table', 'view', 'trigger', 'index')"
        " AND substr(name, 1, 7) != 'sqlite_'"
    ).fetchall()
    tables = {row[1] for row in schema if row[0] == 'table'}
    identity = conn.execute("PRAGMA application_id").fetchone()[0]
    if tables - ALLOWED_TABLES or identity not in (0, APPLICATION_ID):
        raise RuntimeError("Refusing non-member database (exam/unknown tables or identity)")
    if (schema or not initializing) and identity != APPLICATION_ID:
        raise RuntimeError("Refusing unmarked database; use a fresh member database, never import exam accounts")


@contextmanager
def connection(*, initializing=False):
    config.validate()
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        _guard(conn, initializing)
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with connection(initializing=True) as conn:
        conn.executescript(SCHEMA)
        conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")
