from io import BytesIO

import polars as pl

from app.storage.azure_blob import AzureBlobStorage


class AzureParquetRepository:
    def __init__(self, storage: AzureBlobStorage) -> None:
        self._storage = storage

    def list_folders(self) -> list[str]:
        return self._storage.list_folders()

    def list_datasets(self, prefix: str | None = None) -> list[str]:
        return self._storage.list_parquet_blobs(prefix)

    def read(self, blob_name: str) -> pl.DataFrame:
        parquet_bytes = self._storage.download_blob(blob_name)
        return pl.read_parquet(BytesIO(parquet_bytes))
