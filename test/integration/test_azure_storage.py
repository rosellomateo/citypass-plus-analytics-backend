import os

import pytest

from app.core.config import AzureStorageSettings
from app.repositories.parquet_repository import AzureParquetRepository
from app.storage.azure_blob import AzureBlobStorage

pytestmark = pytest.mark.azure


@pytest.mark.skipif(
    os.getenv("RUN_AZURE_INTEGRATION_TESTS") != "true",
    reason="Requiere RUN_AZURE_INTEGRATION_TESTS=true y credenciales locales de Azure",
)
def test_can_list_and_read_a_gold_parquet() -> None:
    settings = AzureStorageSettings.from_environment()

    with AzureBlobStorage(settings) as storage:
        repository = AzureParquetRepository(storage)
        folders = repository.list_folders()
        assert folders, "No se encontraron carpetas en el contenedor Gold"

        blobs = [blob for folder in folders for blob in repository.list_datasets(folder)]
        assert blobs, "No se encontraron archivos Parquet en el contenedor Gold"

        frame = repository.read(blobs[0])

    assert frame.height > 0
    assert frame.width > 0
