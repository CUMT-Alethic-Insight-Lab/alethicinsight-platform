import json
import os
from pathlib import Path
import stat
import subprocess
import time
import types

import pytest


from alethicinsight_cli import credentials
from alethicinsight_cli.client import CliError


BASE = "https://example.com/recruitment"


def security_state(path):
    if os.name != "nt":
        info = path.stat()
        return info.st_uid, stat.S_IMODE(info.st_mode)
    escaped = str(path).replace("'", "''")
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
         f"(Get-Acl -LiteralPath '{escaped}').Sddl"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def make_public(path, directory=False):
    if os.name != "nt":
        path.chmod(0o755 if directory else 0o644)
        return
    escaped = str(path).replace("'", "''")
    script = (
        "$ErrorActionPreference='Stop';"
        f"$p='{escaped}';$acl=Get-Acl -LiteralPath $p;"
        "$everyone=New-Object System.Security.Principal.SecurityIdentifier('S-1-1-0');"
        "$rule=New-Object System.Security.AccessControl.FileSystemAccessRule($everyone,'Read','Allow');"
        "$acl.AddAccessRule($rule);"
        f"[System.IO.{'Directory' if directory else 'File'}]::SetAccessControl($p,$acl)"
    )
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                   check=True, capture_output=True, text=True)


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("directory", [False, True])
def test_load_rejects_public_credentials_without_reading_or_repairing(tmp_path, monkeypatch, legacy, directory):
    monkeypatch.delenv("ALETHICINSIGHT_CONFIG_DIR", raising=False)
    monkeypatch.delenv("ALETHIC_CONFIG_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    store = credentials.CredentialStore()
    path = store.legacy_path if legacy else store.path
    path.parent.mkdir()
    credentials.private_path(path.parent, directory=True)
    path.write_text(json.dumps({"base_url": BASE, "token": "test-only-token", "expires_at": time.time() + 300, "scopes": []}))
    credentials.private_path(path)
    assert store.load(BASE)["token"] == "test-only-token"
    insecure = path.parent if directory else path
    make_public(insecure, directory=directory)
    before = security_state(insecure)
    monkeypatch.setattr(Path, "read_text", lambda *a, **kw: pytest.fail("must reject before reading token"))
    monkeypatch.setattr(credentials, "private_path", lambda *a, **kw: pytest.fail("load must not repair ACLs"))
    with pytest.raises(CliError) as exc:
        store.load(BASE)
    assert exc.value.payload["error"]["code"] == "AUTH_REQUIRED"
    assert "auth login" in str(exc.value)
    assert security_state(insecure) == before


def test_public_fallback_barrier_is_not_a_credential(tmp_path, monkeypatch):
    monkeypatch.setenv("ALETHICINSIGHT_CONFIG_DIR", str(tmp_path / "config"))
    store = credentials.CredentialStore()
    store.save(BASE, {"token": "test-only-token", "expires_at": time.time() + 300, "scopes": []})
    store.block_path.write_text("Legacy credential fallback disabled.\n")
    make_public(store.block_path)
    assert store.load(BASE)["token"] == "test-only-token"


def test_linked_fallback_barrier_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("ALETHICINSIGHT_CONFIG_DIR", str(tmp_path / "config"))
    store = credentials.CredentialStore()
    store.save(BASE, {"token": "test-only-token", "expires_at": time.time() + 300, "scopes": []})
    target = tmp_path / "marker"
    target.write_text("Legacy credential fallback disabled.\n")
    os.link(target, store.block_path)
    with pytest.raises(CliError):
        store.load(BASE)


@pytest.mark.parametrize("uid,mode,accepted", [(123, 0o600, True), (123, 0o700, True),
                                               (456, 0o600, False), (123, 0o640, False),
                                               (123, 0o604, False), (123, 0o711, False)])
def test_posix_verifies_owner_and_group_other_bits(monkeypatch, uid, mode, accepted):
    path = types.SimpleNamespace(stat=lambda: types.SimpleNamespace(st_uid=uid, st_mode=mode))
    monkeypatch.setattr(credentials, "safe_path", lambda *a, **kw: path)
    monkeypatch.setattr(credentials, "os", types.SimpleNamespace(name="posix", getuid=lambda: 123))
    if accepted:
        credentials.verify_private_path(path)
    else:
        with pytest.raises(OSError):
            credentials.verify_private_path(path)


def test_load_acl_inspection_failure_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("ALETHICINSIGHT_CONFIG_DIR", str(tmp_path / "config"))
    store = credentials.CredentialStore()
    store.save(BASE, {"token": "test-only-token", "expires_at": time.time() + 300, "scopes": []})

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "powershell.exe")

    monkeypatch.setattr(credentials, "verify_private_path", fail)
    with pytest.raises(CliError) as exc:
        store.load(BASE)
    assert exc.value.payload["error"]["code"] == "AUTH_REQUIRED"
