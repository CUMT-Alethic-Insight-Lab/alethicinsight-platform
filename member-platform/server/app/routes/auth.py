from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from .. import auth, db
from ..org_auth import revoke_cli

router = APIRouter(prefix="/api/auth", tags=["members"])
HEX64 = r"^[0-9a-f]{64}$"


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: str = Field(min_length=1, max_length=80)
    client_hash: str = Field(pattern=HEX64)


class ChangePasswordBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    old_client_hash: str = Field(pattern=HEX64)
    new_salt: str = Field(pattern=r"^[0-9a-f]{32}$")
    new_client_hash: str = Field(pattern=HEX64)


def get_session(request):
    with db.connection() as conn:
        sess = auth.lookup_session(conn, auth.bearer_token(request))
        if sess is None:
            raise auth.unauthorized()
        acct = conn.execute("SELECT * FROM account WHERE student_id = ?", (sess["student_id"],)).fetchone()
    if acct is None or acct["role"] not in ("member", "admin"):
        raise auth.unauthorized()
    return sess, acct


def payload(acct):
    return {"student_id": acct["student_id"], "nickname": acct["nickname"],
            "role": acct["role"], "pw_changed": bool(acct["pw_changed"])}


def rate_keys(request, student_id):
    return (student_id, "ip:" + auth.client_ip(request))


@router.get("/salt")
def salt(student_id: str, request: Request, response: Response):
    if not 1 <= len(student_id) <= 80:
        raise HTTPException(400, "无效账号")
    response.headers["Cache-Control"] = "no-store"
    with db.connection() as conn:
        for key in rate_keys(request, student_id):
            auth.check_login_rate(conn, key)
        row = conn.execute("SELECT pw_salt FROM account WHERE student_id = ?", (student_id,)).fetchone()
    return {"salt": row["pw_salt"] if row and row["pw_salt"] else auth.pseudo_salt(student_id)}


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response):
    keys = rate_keys(request, body.student_id)
    with db.connection() as conn:
        for key in keys:
            auth.check_login_rate(conn, key)
        acct = conn.execute("SELECT * FROM account WHERE student_id = ?", (body.student_id,)).fetchone()
        valid = auth.verify_client_hash(acct["pw_hash"] if acct else None, body.client_hash)
        if acct and acct["role"] not in ("member", "admin"):
            valid = False
    if not valid:
        for key in keys:
            auth.record_login_failure(key)
        raise HTTPException(401, "账号或密码错误")
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = conn.execute("SELECT * FROM account WHERE student_id = ?", (body.student_id,)).fetchone()
        if current is None or current["role"] != acct["role"] or current["pw_hash"] != acct["pw_hash"]:
            raise auth.unauthorized()
        auth.clear_login_failures(conn, body.student_id)
        token = auth.issue_session(conn, acct["role"], None, acct["student_id"])
    response.headers["Cache-Control"] = "no-store"
    return {"token": token, **payload(acct)}


@router.get("/me")
def me(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return payload(get_session(request)[1])


@router.post("/change_password")
def change_password(body: ChangePasswordBody, request: Request):
    sess, acct = get_session(request)
    if body.new_salt == acct["pw_salt"]:
        raise HTTPException(400, "请使用新盐值")
    if body.new_client_hash == auth.compute_client_hash(acct["student_id"], body.new_salt) or any(
        body.new_client_hash == auth.compute_client_hash(weak, body.new_salt) for weak in auth.WEAK_PASSWORDS
    ):
        raise HTTPException(400, "新密码过于常见或与账号相同")
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = conn.execute("SELECT * FROM account WHERE student_id = ?", (acct["student_id"],)).fetchone()
        if auth.lookup_session(conn, auth.bearer_token(request)) is None or current["pw_hash"] != acct["pw_hash"]:
            raise auth.unauthorized()
        if not auth.verify_client_hash(current["pw_hash"], body.old_client_hash):
            raise HTTPException(401, "原密码错误")
        conn.execute("UPDATE account SET pw_salt=?, pw_hash=?, pw_changed=1, updated_at=? WHERE student_id=?",
                     (body.new_salt, auth.store_hash(body.new_client_hash), auth._utcnow().isoformat(), acct["student_id"]))
        conn.execute("DELETE FROM login_session WHERE student_id=? AND token_hash != ?", (acct["student_id"], sess["token_hash"]))
        revoke_cli(conn, acct["student_id"])
        auth.write_audit(conn, acct["student_id"], "change_password", acct["student_id"])
    return {"ok": True}


@router.post("/logout")
def logout(request: Request):
    sess, _ = get_session(request)
    with db.connection() as conn:
        conn.execute("DELETE FROM login_session WHERE token_hash=?", (sess["token_hash"],))
    return {"ok": True}
