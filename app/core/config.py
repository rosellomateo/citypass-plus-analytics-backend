import os
from dataclasses import dataclass, field
from urllib.parse import urlparse


class ConfigurationError(ValueError):
    """Raised when required application configuration is invalid or missing."""


@dataclass(frozen=True, slots=True)
class AzureStorageSettings:
    account_url: str
    container_name: str
    sas_token: str = field(repr=False)

    @classmethod
    def from_environment(cls) -> "AzureStorageSettings":
        names = (
            "AZURE_STORAGE_ACCOUNT_URL",
            "AZURE_STORAGE_CONTAINER",
            "AZURE_STORAGE_SAS_TOKEN",
        )
        values = {name: os.getenv(name, "").strip() for name in names}
        missing = [name for name, value in values.items() if not value]

        if missing:
            raise ConfigurationError(
                f"Faltan variables de entorno requeridas: {', '.join(missing)}"
            )

        account_url = values["AZURE_STORAGE_ACCOUNT_URL"].rstrip("/")
        parsed_url = urlparse(account_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ConfigurationError("AZURE_STORAGE_ACCOUNT_URL debe ser una URL HTTPS válida")

        sas_token = values["AZURE_STORAGE_SAS_TOKEN"].removeprefix("?")
        if not sas_token:
            raise ConfigurationError("AZURE_STORAGE_SAS_TOKEN no puede estar vacío")

        return cls(
            account_url=account_url,
            container_name=values["AZURE_STORAGE_CONTAINER"],
            sas_token=sas_token,
        )
