from io import BytesIO
from unittest.mock import MagicMock

import polars as pl

from app.repositories.parquet_repository import AzureParquetRepository


def test_lists_datasets_with_prefix() -> None:
    storage = MagicMock()
    storage.list_parquet_blobs.return_value = ["Reclamos/data.parquet"]
    repository = AzureParquetRepository(storage)

    result = repository.list_datasets("Reclamos")

    assert result == ["Reclamos/data.parquet"]
    storage.list_parquet_blobs.assert_called_once_with("Reclamos")


def test_reads_downloaded_parquet() -> None:
    buffer = BytesIO()
    expected = pl.DataFrame({"categoria": ["Alumbrado"], "cantidad": [3]})
    expected.write_parquet(buffer)
    storage = MagicMock()
    storage.download_blob.return_value = buffer.getvalue()
    repository = AzureParquetRepository(storage)

    result = repository.read("Reclamos/data.parquet")

    assert result.equals(expected)
    storage.download_blob.assert_called_once_with("Reclamos/data.parquet")
