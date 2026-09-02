from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.config import AzureStorageSettings
from app.storage.azure_blob import AzureBlobStorage


def make_settings() -> AzureStorageSettings:
    return AzureStorageSettings(
        account_url="https://storage.blob.core.windows.net",
        container_name="gold",
        sas_token="secret",
    )


def test_lists_only_sorted_parquet_blobs() -> None:
    client = MagicMock()
    client.list_blobs.return_value = [
        SimpleNamespace(name="Reclamos/data.parquet"),
        SimpleNamespace(name="readme.txt"),
        SimpleNamespace(name="Emergencias/data.PARQUET"),
    ]
    storage = AzureBlobStorage(make_settings(), container_client=client)

    result = storage.list_parquet_blobs(prefix="Reclamos")

    assert result == ["Emergencias/data.PARQUET", "Reclamos/data.parquet"]
    client.list_blobs.assert_called_once_with(name_starts_with="Reclamos")


def test_downloads_blob_and_closes_client() -> None:
    client = MagicMock()
    client.get_blob_client.return_value.download_blob.return_value.readall.return_value = b"data"

    with AzureBlobStorage(make_settings(), container_client=client) as storage:
        result = storage.download_blob("Reclamos/data.parquet")

    assert result == b"data"
    client.get_blob_client.assert_called_once_with("Reclamos/data.parquet")
    client.close.assert_called_once_with()
