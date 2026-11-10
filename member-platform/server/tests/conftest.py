import os
import sys
from pathlib import Path

os.environ["MEMBER_PLATFORM_SECRET_KEY"] = "member-tests-only-separate-secret-2026-unique"
os.environ["MEMBER_PLATFORM_DB_PATH"] = str(Path(__file__).parent / "unused-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
