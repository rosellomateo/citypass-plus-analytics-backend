from collections.abc import Iterator

from app.core.config import AzureStorageSettings
from app.repositories.parquet_repository import AzureParquetRepository
from app.storage.azure_blob import AzureBlobStorage


def obtener_repositorio() -> Iterator[AzureParquetRepository]:
    settings = AzureStorageSettings.from_environment()

    # el 'with' cierra el cliente de Azure cuando termina el uso de la dependencia.
    with AzureBlobStorage(settings) as storage:
        yield AzureParquetRepository(storage)
