import json
from typing import Any

from app.storage.azure_blob import AzureBlobStorage


class AzureJsonRepository:
    def __init__(self, storage: AzureBlobStorage) -> None:
        self._storage = storage

    def read(self, blob_name: str) -> dict[str, Any]:
        contenido = self._storage.download_blob(blob_name)
        datos = json.loads(contenido)

        if not isinstance(datos, dict):
            raise ValueError(f"Se esperaba un objeto JSON en el archivo {blob_name}.")

        return datos
