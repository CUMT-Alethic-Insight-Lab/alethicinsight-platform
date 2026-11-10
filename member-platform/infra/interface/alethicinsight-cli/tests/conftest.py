import pytest


@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch, tmp_path):
    for name in ("ALETHICINSIGHT_API_BASE_URL", "ALETHIC_API_BASE_URL", "ALETHIC_BASE_URL",
                 "ALETHICINSIGHT_CONFIG_DIR", "ALETHIC_CONFIG_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
