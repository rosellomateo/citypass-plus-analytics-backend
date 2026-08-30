from types import TracebackType
from typing import Protocol, Self

from azure.storage.blob import ContainerClient

from app.core.config import AzureStorageSettings


class _ContainerClient(Protocol):
    def list_blobs(self, *, name_starts_with: str | None = None) -> object: ...

    def get_blob_client(self, blob: str) -> object: ...

    def close(self) -> None: ...


class AzureBlobStorage:
    """Read-only access to the Gold container in Azure Blob Storage."""

    def __init__(
        self,
        settings: AzureStorageSettings,
        container_client: _ContainerClient | None = None,
    ) -> None:
        self._client = container_client or ContainerClient(
            account_url=settings.account_url,
            container_name=settings.container_name,
            credential=settings.sas_token,
        )

    def list_parquet_blobs(self, prefix: str | None = None) -> list[str]:
        blobs = self._client.list_blobs(name_starts_with=prefix)
        names = (blob.name for blob in blobs)
        return sorted(name for name in names if name.lower().endswith(".parquet"))

    def download_blob(self, blob_name: str) -> bytes:
        blob_client = self._client.get_blob_client(blob_name)
        return blob_client.download_blob().readall()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
