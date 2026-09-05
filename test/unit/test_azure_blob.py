from types import SimpleNamespace
from unittest.mock import MagicMock

from azure.storage.blob import BlobPrefix

from app.core.config import AzureStorageSettings
from app.storage.azure_blob import AzureBlobStorage


def make_settings() -> AzureStorageSettings:
    return AzureStorageSettings(
        account_url="https://storage.blob.core.windows.net",
        container_name="gold",
        sas_token="secret",
    )


def make_blob_prefix(name: str) -> BlobPrefix:
    prefix = BlobPrefix()
    prefix.name = name
    return prefix


def test_lists_sorted_folders_without_trailing_separator() -> None:
    client = MagicMock()
    client.walk_blobs.return_value = [
        make_blob_prefix("Reclamos/"),
        SimpleNamespace(name="readme.txt"),
        make_blob_prefix("Emergencia y Seguridad/"),
    ]
    storage = AzureBlobStorage(make_settings(), container_client=client)

    result = storage.list_folders()

    assert result == ["Emergencia y Seguridad", "Reclamos"]
    client.walk_blobs.assert_called_once_with(name_starts_with=None, delimiter="/")


def test_lists_only_sorted_parquet_blobs_from_exact_folder() -> None:
    client = MagicMock()
    client.list_blobs.return_value = [
        SimpleNamespace(name="Reclamos/second.parquet"),
        SimpleNamespace(name="Reclamos/readme.txt"),
        SimpleNamespace(name="Reclamos/first.PARQUET"),
    ]
    storage = AzureBlobStorage(make_settings(), container_client=client)

    result = storage.list_parquet_blobs(prefix="Reclamos")

    assert result == ["Reclamos/first.PARQUET", "Reclamos/second.parquet"]
    client.list_blobs.assert_called_once_with(name_starts_with="Reclamos/")


def test_accepts_folder_with_separators() -> None:
    client = MagicMock()
    client.list_blobs.return_value = []
    storage = AzureBlobStorage(make_settings(), container_client=client)

    storage.list_parquet_blobs(prefix="/Reclamos/")

    client.list_blobs.assert_called_once_with(name_starts_with="Reclamos/")


def test_downloads_blob_and_closes_client() -> None:
    client = MagicMock()
    client.get_blob_client.return_value.download_blob.return_value.readall.return_value = (
        b"data"
    )

    with AzureBlobStorage(make_settings(), container_client=client) as storage:
        result = storage.download_blob("Reclamos/data.parquet")

    assert result == b"data"
    client.get_blob_client.assert_called_once_with("Reclamos/data.parquet")
    client.close.assert_called_once_with()
