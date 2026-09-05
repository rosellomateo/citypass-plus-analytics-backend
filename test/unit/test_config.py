import pytest

from app.core.config import AzureStorageSettings, ConfigurationError


def test_loads_azure_storage_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "AZURE_STORAGE_ACCOUNT_URL", "https://storage.blob.core.windows.net/"
    )
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "gold")
    monkeypatch.setenv("AZURE_STORAGE_SAS_TOKEN", "?sp=rl&sig=secret")

    settings = AzureStorageSettings.from_environment()

    assert settings.account_url == "https://storage.blob.core.windows.net"
    assert settings.container_name == "gold"
    assert settings.sas_token == "sp=rl&sig=secret"
    assert "secret" not in repr(settings)


def test_reports_missing_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "AZURE_STORAGE_ACCOUNT_URL",
        "AZURE_STORAGE_CONTAINER",
        "AZURE_STORAGE_SAS_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ConfigurationError, match="AZURE_STORAGE_ACCOUNT_URL"):
        AzureStorageSettings.from_environment()


def test_rejects_non_https_account_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "AZURE_STORAGE_ACCOUNT_URL", "http://storage.blob.core.windows.net"
    )
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "gold")
    monkeypatch.setenv("AZURE_STORAGE_SAS_TOKEN", "sp=rl&sig=secret")

    with pytest.raises(ConfigurationError, match="URL HTTPS"):
        AzureStorageSettings.from_environment()
