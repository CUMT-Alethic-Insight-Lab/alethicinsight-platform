import secrets
import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from .. import auth, config, db
from ..org_auth import revoke_cli

router = APIRouter(prefix="/api/admin/accounts", tags=["member administration"])
admin_router = APIRouter(prefix="/api/admin", tags=["member administration"])


class RoleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["member", "admin", "inactive", "applicant"]


class CreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    nickname: str = Field(default="", max_length=80)
    role: Literal["member", "admin"] = "member"


def actor_in_transaction(conn, request):
    if config.IS_EDGE:
        raise HTTPException(503, "成员管理仅允许 authoritative 实例", headers={"Retry-After": "60"})
    sess = auth.lookup_session(conn, auth.bearer_token(request))
    if sess is None or sess["kind"] != "admin":
        raise auth.unauthorized()
    acct = conn.execute("SELECT * FROM account WHERE student_id=?", (sess["student_id"],)).fetchone()
    if not acct["pw_changed"]:
        raise auth.force_password_change()
    return sess["student_id"]


def set_temporary_password(conn, student_id):
    password = secrets.token_urlsafe(24)
    salt = auth.new_salt()
    conn.execute("UPDATE account SET pw_salt=?, pw_hash=?, pw_changed=0, updated_at=? WHERE student_id=?",
                 (salt, auth.store_hash(auth.compute_client_hash(password, salt)), auth._utcnow().isoformat(), student_id))
    conn.execute("DELETE FROM login_session WHERE student_id=?", (student_id,))
    revoke_cli(conn, student_id)
    auth.clear_login_failures(conn, student_id)
    return password


@router.get("")
def list_accounts(role: str | None = None, q: str | None = None, _: None = Depends(auth.require_admin)):
    with db.connection() as conn:
        rows = conn.execute("SELECT student_id, nickname, role, pw_changed, created_at, updated_at FROM account ORDER BY created_at DESC, student_id").fetchall()
    return {"items": [dict(r) for r in rows if (not role or r["role"] == role) and
                     (not q or q.lower() in (r["student_id"] + " " + r["nickname"]).lower())]}


@router.post("", status_code=201)
def create_account(body: CreateBody, request: Request, response: Response):
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        actor = actor_in_transaction(conn, request)
        now = auth._utcnow().isoformat()
        try:
            conn.execute("INSERT INTO account (student_id,nickname,role,created_at,updated_at) VALUES (?,?,?,?,?)",
                         (body.student_id, body.nickname, body.role, now, now))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "账号已存在")
        password = set_temporary_password(conn, body.student_id)
        auth.write_audit(conn, actor, "create_member", body.student_id, body.role)
    response.headers["Cache-Control"] = "no-store"
    return {"student_id": body.student_id, "temporary_password": password, "pw_changed": False}


@router.post("/{student_id}/role")
def set_role(student_id: str, body: RoleBody, request: Request):
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        actor = actor_in_transaction(conn, request)
        acct = conn.execute("SELECT * FROM account WHERE student_id=?", (student_id,)).fetchone()
        if acct is None:
            raise HTTPException(404, "未找到账号")
        if acct["role"] == "admin" and body.role != "admin":
            if actor == student_id:
                raise HTTPException(400, "不能降级当前登录的管理员账号")
            if conn.execute("SELECT COUNT(*) FROM account WHERE role='admin'").fetchone()[0] <= 1:
                raise HTTPException(400, "至少保留一名管理员")
        conn.execute("UPDATE account SET role=?, updated_at=? WHERE student_id=?", (body.role, auth._utcnow().isoformat(), student_id))
        if acct["role"] != body.role:
            conn.execute("DELETE FROM login_session WHERE student_id=?", (student_id,))
            revoke_cli(conn, student_id)
        auth.write_audit(conn, actor, "set_role", student_id, f"{acct['role']} -> {body.role}")
    return {"ok": True}


@router.post("/{student_id}/reset_password")
def reset_password(student_id: str, request: Request, response: Response):
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        actor = actor_in_transaction(conn, request)
        if not conn.execute("SELECT 1 FROM account WHERE student_id=?", (student_id,)).fetchone():
            raise HTTPException(404, "未找到账号")
        password = set_temporary_password(conn, student_id)
        auth.write_audit(conn, actor, "reset_password", student_id)
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True, "temporary_password": password, "pw_changed": False}


@admin_router.get("/audit_log")
def audit_log(_: None = Depends(auth.require_admin)):
    with db.connection() as conn:
        return {"items": [dict(r) for r in conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 200")]}
