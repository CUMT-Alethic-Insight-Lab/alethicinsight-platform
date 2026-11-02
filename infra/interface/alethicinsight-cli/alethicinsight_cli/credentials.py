import datetime
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time

from .client import CliError, normalize_base


def expiry_timestamp(value):
    try:
        if isinstance(value, bool):
            raise ValueError()
        if isinstance(value, (int, float)):
            result = float(value)
        else:
            parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError()
            result = parsed.timestamp()
        if not math.isfinite(result):
            raise ValueError()
        return result
    except (TypeError, ValueError, AttributeError, OverflowError):
        raise auth_required() from None


def auth_required():
    return CliError("AUTH_REQUIRED", "Credentials are missing, invalid or expired; run alethicinsight-cli auth login.", 3)


def safe_path(path, directory=False):
    path = Path(path).absolute()
    if ".." in path.parts or (os.name == "nt" and (str(path).startswith("\\\\") or any(":" in p for p in path.parts[1:]))):
        raise OSError("Unsafe credential path")
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise OSError("Linked credential path")
        if item == path and not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
            raise OSError("Unexpected credential path type")
        if item == path and not directory and info.st_nlink != 1:
            raise OSError("Hard-linked credential file")
    return path


def private_path(path, directory=False):
    if os.name == "nt":
        escaped = str(path).replace("'", "''")
        inheritance = "ContainerInherit,ObjectInherit" if directory else "None"
        script = (
            "$ErrorActionPreference='Stop';"
            f"$p='{escaped}';"
            "$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User;"
            "$acl=Get-Acl -LiteralPath $p;"
            "if($acl.GetOwner([System.Security.Principal.SecurityIdentifier]) -ne $sid){throw 'Unsafe credential owner'};"
            "$acl.SetAccessRuleProtection($true,$false);"
            "foreach($old in @($acl.GetAccessRules($true,$false,[System.Security.Principal.SecurityIdentifier])))"
            "{$acl.RemoveAccessRuleSpecific($old)};"
            f"$rule=New-Object System.Security.AccessControl.FileSystemAccessRule($sid,'FullControl','{inheritance}','None','Allow');"
            "$acl.AddAccessRule($rule);"
            f"[System.IO.{'Directory' if directory else 'File'}]::SetAccessControl($p,$acl);"
            "$actual=Get-Acl -LiteralPath $p;"
            "$rules=@($actual.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]));"
            "if(!$actual.AreAccessRulesProtected -or $rules.Count -ne 1 -or "
            "$rules[0].IdentityReference -ne $sid -or $rules[0].IsInherited -or "
            "$rules[0].AccessControlType -ne 'Allow' -or $rules[0].FileSystemRights -ne 'FullControl')"
            "{throw 'Unsafe final credential ACL'}"
        )
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                       check=True, capture_output=True, text=True)
    else:
        path.chmod(0o700 if directory else 0o600)


class CredentialStore:
    def __init__(self):
        override = os.environ.get("ALETHICINSIGHT_CONFIG_DIR", os.environ.get("ALETHIC_CONFIG_DIR"))
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) if os.name == "nt" else Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        self.directory = Path(override) if override is not None else root / ("AlethicInsight" if os.name == "nt" else "alethicinsight")
        self.legacy_path = None if override is not None else root / ("Alethic" if os.name == "nt" else "alethic") / "credentials.json"
        self.path = self.directory / "credentials.json"
        self.block_path = self.directory / "legacy-disabled"

    def load(self, base):
        try:
            safe_path(self.directory, directory=True)
            path = safe_path(self.path)
            safe_path(self.block_path)
            if not path.exists() and not self.block_path.exists() and self.legacy_path is not None:
                path = safe_path(self.legacy_path)
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or normalize_base(value.get("base_url")) != normalize_base(base):
                raise ValueError()
            if not isinstance(value.get("token"), str) or not value["token"] or any(ord(c) < 33 or ord(c) > 126 for c in value["token"]):
                raise ValueError()
            if not isinstance(value.get("scopes"), list) or not all(isinstance(s, str) for s in value["scopes"]):
                raise ValueError()
            if expiry_timestamp(value.get("expires_at")) <= time.time():
                raise ValueError()
            return value
        except (OSError, ValueError, TypeError, CliError):
            raise auth_required() from None

    def _write(self, path, content):
        temporary = None
        try:
            safe_path(self.directory, directory=True)
            safe_path(path)
            if self.directory.absolute() in (Path.home().absolute(), Path.cwd().absolute()) or self.directory.absolute() == self.directory.absolute().parent:
                raise OSError("Credential directory must be dedicated")
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            if any(item.name not in {"credentials.json", "legacy-disabled"} for item in self.directory.iterdir()):
                raise OSError("Credential directory is not dedicated")
            private_path(self.directory, directory=True)
            fd, temporary = tempfile.mkstemp(prefix="credentials-", dir=self.directory)
            os.close(fd)
            temporary = Path(temporary)
            private_path(temporary)
            temporary.write_text(content, encoding="utf-8")
            safe_path(path)
            os.replace(temporary, path)
            try:
                private_path(path)
            except (OSError, subprocess.SubprocessError):
                safe_path(path).unlink(missing_ok=True)
                raise
        except (OSError, subprocess.SubprocessError):
            raise CliError("CREDENTIAL_STORAGE_FAILED", "Could not secure local credentials; no token was printed.", 5) from None
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)

    def save(self, base, value):
        token = value.get("token")
        scopes = value.get("scopes")
        if not isinstance(token, str) or not token or any(ord(c) < 33 or ord(c) > 126 for c in token) or not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
            raise CliError("API_UNAVAILABLE", "Token exchange returned invalid credentials.", 5)
        if expiry_timestamp(value.get("expires_at")) <= time.time():
            raise auth_required()
        self._write(self.path, json.dumps({"base_url": normalize_base(base), "token": token, "expires_at": value["expires_at"], "scopes": scopes}))

    def delete(self):
        self._write(self.block_path, "Legacy credential fallback disabled.\n")
        try:
            safe_path(self.path).unlink(missing_ok=True)
        except OSError:
            raise CliError("CREDENTIAL_STORAGE_FAILED", "Could not delete local credentials.", 5) from None
