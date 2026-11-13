from collections.abc import Iterator

from app.core.config import AzureStorageSettings
from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.storage.azure_blob import AzureBlobStorage


def obtener_repositorio() -> Iterator[AzureParquetRepository]:
    settings_gold = AzureStorageSettings.from_environment()

    # el 'with' cierra el cliente de Azure cuando termina el uso de la dependencia.
    with AzureBlobStorage(settings_gold) as storage_gold:
        yield AzureParquetRepository(storage_gold)


def obtener_repositorio_informes() -> Iterator[AzureJsonRepository]:
    settings_analisis = AzureStorageSettings.from_environment(prefix="AZURE_ANALISIS")

    with AzureBlobStorage(settings_analisis) as storage_analisis:
        yield AzureJsonRepository(storage_analisis)
