import pytest

from app.core.config import AzureStorageSettings, ConfigurationError, CorsSettings


def test_cors_settings_use_local_frontend_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    settings = CorsSettings.from_environment()

    assert settings.allowed_origins == ("http://localhost:5173",)


def test_cors_settings_parse_multiple_unique_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173, https://analytics.example.com/,http://localhost:5173",
    )

    settings = CorsSettings.from_environment()

    assert settings.allowed_origins == (
        "http://localhost:5173",
        "https://analytics.example.com",
    )


@pytest.mark.parametrize(
    "origins",
    (
        "*",
        "analytics.example.com",
        "https://analytics.example.com/path",
    ),
)
def test_cors_settings_reject_invalid_origins(
    monkeypatch: pytest.MonkeyPatch,
    origins: str,
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", origins)

    with pytest.raises(ConfigurationError):
        CorsSettings.from_environment()


def test_loads_azure_storage_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_URL", "https://storage.blob.core.windows.net/")
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
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_URL", "http://storage.blob.core.windows.net")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "gold")
    monkeypatch.setenv("AZURE_STORAGE_SAS_TOKEN", "sp=rl&sig=secret")

    with pytest.raises(ConfigurationError, match="URL HTTPS"):
        AzureStorageSettings.from_environment()
