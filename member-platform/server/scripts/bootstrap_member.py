import argparse
import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import auth, config, db


def bootstrap(student_id, password):
    if config.IS_EDGE:
        raise RuntimeError("Bootstrap requires an authoritative instance")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", student_id):
        raise ValueError("Invalid administrator ID")
    if len(password) < 12 or password == student_id or password in auth.WEAK_PASSWORDS:
        raise ValueError("Use a unique bootstrap password of at least 12 characters")
    db.init_db()
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT COUNT(*) FROM account").fetchone()[0]:
            raise RuntimeError("Bootstrap is only allowed for an empty member database")
        salt = auth.new_salt()
        now = auth._utcnow().isoformat()
        conn.execute("INSERT INTO account (student_id,role,pw_salt,pw_hash,pw_changed,created_at,updated_at) VALUES (?,'admin',?,?,0,?,?)",
                     (student_id, salt, auth.store_hash(auth.compute_client_hash(password, salt)), now, now))
        auth.write_audit(conn, student_id, "bootstrap_admin", student_id)


def main():
    parser = argparse.ArgumentParser(description="Explicit first administrator bootstrap; never imports exam accounts")
    parser.add_argument("--student-id", required=True)
    args = parser.parse_args()
    password = getpass.getpass("Unique temporary administrator password (12+ characters): ")
    if password != getpass.getpass("Repeat password: "):
        raise ValueError("Passwords do not match")
    bootstrap(args.student_id, password)
    print("Administrator created; log in at /login and change the temporary password.")


if __name__ == "__main__":
    main()
