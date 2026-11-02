import os
import shutil
import subprocess
from pathlib import Path

import pytest


BASH = shutil.which("bash")
SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "push-lab.sh"
pytestmark = pytest.mark.skipif(BASH is None, reason="Bash is required to verify deployment packaging")


def run_push(tmp_path, kit_dir):
    calls = tmp_path / "ssh-calls.txt"
    archives = tmp_path / "archive-files.txt"
    env = os.environ.copy()
    env.update({
        "LAB_HOST": "synthetic@example.invalid",
        "SSH_KEY": str(tmp_path / "nonexistent-key"),
        "MOCK_CALLS": calls.as_posix(),
        "MOCK_ARCHIVES": archives.as_posix(),
    })
    env.pop("EXAM_KIT_DIR", None)
    if kit_dir is not None:
        env["EXAM_KIT_DIR"] = kit_dir
    result = subprocess.run(
        [BASH, "-c", '''
ssh() {
  printf 'mock ssh\n' >> "$MOCK_CALLS"
  if [[ "$*" == *"tar xzf"* ]]; then
    tar tzf - >> "$MOCK_ARCHIVES"
  fi
}
export -f ssh
bash "$1"
''', "deploy-test", SCRIPT.as_posix()],
        env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=30,
    )
    return result, calls, archives


@pytest.mark.parametrize("source", ["unset", "relative", "missing"])
def test_missing_exam_kit_fails_before_ssh(tmp_path, source):
    kit_dir = {
        "unset": None,
        "relative": "relative-exam-kit",
        "missing": (tmp_path / "missing-exam-kit").as_posix(),
    }[source]
    result, calls, archives = run_push(tmp_path, kit_dir)
    assert result.returncode != 0
    assert not calls.exists()
    assert not archives.exists()


def test_push_lab_packages_receiver_from_separate_checkout(tmp_path):
    kit_dir = tmp_path / "separate exam kit"
    kit_dir.mkdir()
    (kit_dir / "session_receiver.py").write_text("print('synthetic receiver')\n", encoding="utf-8")
    result, calls, archives = run_push(tmp_path, kit_dir.as_posix())
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert len(calls.read_text().splitlines()) == 6
    files = archives.read_text().splitlines()
    assert "app/" in files
    assert "static/" in files
    assert "requirements.txt" in files
    assert files[-1] == "session_receiver.py"
    assert not any("exam_kit/" in name for name in files)
