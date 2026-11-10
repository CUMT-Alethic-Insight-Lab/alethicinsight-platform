import json
import sys

import pytest

from alethicinsight_cli import cli
from alethicinsight_cli.client import BASE_CONFIGURATION_MESSAGE, Client
from alethicinsight_cli.credentials import CredentialStore
from alethicinsight_mcp.server import CliRunner


BASE_VARIABLES = ("ALETHICINSIGHT_API_BASE_URL", "ALETHIC_API_BASE_URL", "ALETHIC_BASE_URL")


@pytest.mark.parametrize("arguments", [
    ["capabilities"], ["auth", "login"], ["auth", "logout"], ["auth", "scopes"],
    ["forms", "schema"], ["applications", "draft", "--file", "unused.json"],
])
@pytest.mark.parametrize("empty", [None, "", "   "])
def test_missing_base_fails_before_credentials_network_or_browser(arguments, empty, monkeypatch, capsys):
    if empty is not None:
        monkeypatch.setenv(BASE_VARIABLES[0], empty)
        monkeypatch.setenv(BASE_VARIABLES[1], "http://127.0.0.1:1")
    monkeypatch.setattr(CredentialStore, "__init__", lambda *a: pytest.fail("must not access credentials"))
    monkeypatch.setattr(Client, "request", lambda *a, **kw: pytest.fail("must not make HTTP requests"))
    monkeypatch.setattr(cli.webbrowser, "open", lambda *a: pytest.fail("must not open browser"))
    assert cli.main([*arguments, "--json", "--non-interactive"]) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert len(captured.out.splitlines()) == 1
    assert json.loads(captured.out) == {"error": {
        "code": "CONFIGURATION_REQUIRED", "message": BASE_CONFIGURATION_MESSAGE}}


@pytest.mark.parametrize("selected", range(3))
def test_environment_alias_precedence_is_preserved(selected, monkeypatch, capsys):
    expected = f"http://127.0.0.1:{8100 + selected}"
    for index in range(selected, 3):
        monkeypatch.setenv(BASE_VARIABLES[index], f"http://127.0.0.1:{8100 + index}")

    def execute(args, client, store):
        assert client.base == expected
        return {"configured": True}

    monkeypatch.setattr(cli, "execute", execute)
    assert cli.main(["capabilities", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"configured": True}


def test_mcp_configuration_error_uses_fixed_message_not_child_secrets():
    script = (
        "import json; print(json.dumps({'error': {'code': 'CONFIGURATION_REQUIRED', "
        "'message': 'Bearer child-secret', 'token': 'do-not-forward'}})); raise SystemExit(2)"
    )
    result = CliRunner((sys.executable, "-c", script)).call("org_capabilities", {})
    assert result["isError"] is True
    assert json.loads(result["content"][0]["text"]) == {"error": {
        "code": "CONFIGURATION_REQUIRED", "message": BASE_CONFIGURATION_MESSAGE}}
    assert "child-secret" not in json.dumps(result)
    assert "do-not-forward" not in json.dumps(result)
