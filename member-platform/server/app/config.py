import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("MEMBER_PLATFORM_DATA_DIR", BASE_DIR / "data")).resolve()
DB_PATH = Path(os.environ.get("MEMBER_PLATFORM_DB_PATH", DATA_DIR / "members.db")).resolve()
SECRET_KEY = os.environ.get("MEMBER_PLATFORM_SECRET_KEY", "")
PUBLIC_PREFIX = os.environ.get("MEMBER_PLATFORM_PUBLIC_PREFIX", "").rstrip("/")
SESSION_DAYS = max(1, min(30, int(os.environ.get("MEMBER_PLATFORM_SESSION_DAYS", "1"))))
ORG_CLI_TOKEN_SECONDS = max(60, min(3600, int(os.environ.get("MEMBER_PLATFORM_ORG_CLI_TOKEN_SECONDS", "900"))))
ORG_CLI_CODE_SECONDS = max(30, min(600, int(os.environ.get("MEMBER_PLATFORM_ORG_CLI_CODE_SECONDS", "300"))))
ORG_CLI_CODE_ATTEMPTS = 5
ROLE = os.environ.get("MEMBER_PLATFORM_ROLE", "authoritative").strip().lower()
IS_EDGE = ROLE == "edge"


def validate():
    if len(SECRET_KEY) < 32 or SECRET_KEY in {"dev-secret-key", os.environ.get("SECRET_KEY")}:
        raise RuntimeError("Set a unique MEMBER_PLATFORM_SECRET_KEY of at least 32 characters; never reuse the exam key")
    if ROLE not in {"authoritative", "edge"}:
        raise RuntimeError("MEMBER_PLATFORM_ROLE must be authoritative or edge")
    if PUBLIC_PREFIX and (not PUBLIC_PREFIX.startswith("/") or any(c not in "/-_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for c in PUBLIC_PREFIX)):
        raise RuntimeError("Invalid MEMBER_PLATFORM_PUBLIC_PREFIX")
    exam_data = BASE_DIR.parents[1] / "server" / "data"
    if DB_PATH == exam_data.resolve() or exam_data.resolve() in DB_PATH.parents:
        raise RuntimeError("Member service cannot use the exam data directory")
    legacy = os.environ.get("ALE_THIC_DB_PATH")
    if legacy and DB_PATH == Path(legacy).resolve():
        raise RuntimeError("Member database must not reuse ALE_THIC_DB_PATH")
    legacy_dir = os.environ.get("ALE_THIC_DATA_DIR")
    if legacy_dir and (Path(legacy_dir).resolve() == DB_PATH.parent or Path(legacy_dir).resolve() in DB_PATH.parents):
        raise RuntimeError("Member database must not use the exam data directory")
