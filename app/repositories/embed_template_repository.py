"""Descarga de una release inmutable del frontend, autenticada con Microsoft Entra."""

import hashlib
import json
import re
from collections.abc import Iterator
from contextlib import contextmanager

from azure.identity import DefaultAzureCredential
from azure.storage.blob import ContainerClient

from app.core.config import EmbedSettings

MODULOS_EMBED = frozenset({"reclamos", "emergencias", "movilidad", "espacios", "residuos"})
MARCADOR_MODULO = "__CITYPASS_MODULO__"
MARCADOR_DATOS = "__CITYPASS_DATOS__"


class InvalidEmbedRelease(ValueError):
    """La release está incompleta o no coincide con su manifiesto y checksums."""


class EmbedTemplateRepository:
    def __init__(self, settings: EmbedSettings) -> None:
        self._settings = settings

    @contextmanager
    def _open_container(self) -> Iterator[ContainerClient]:
        # Managed Identity en Azure; az login para desarrollo local.
        with DefaultAzureCredential(
            managed_identity_client_id=self._settings.managed_identity_client_id,
            exclude_interactive_browser_credential=True,
        ) as credential:
            with ContainerClient(
                account_url=self._settings.account_url,
                container_name=self._settings.container_name,
                credential=credential,
                connection_timeout=5,
                read_timeout=15,
                retry_total=2,
            ) as container:
                yield container

    def _download(self, container: ContainerClient, filename: str, max_bytes: int) -> bytes:
        blob = container.get_blob_client(f"{self._settings.release_prefix}/{filename}")
        content = blob.download_blob(offset=0, length=max_bytes + 1).readall()
        if len(content) > max_bytes:
            raise InvalidEmbedRelease("El archivo de la release supera el tamaño permitido")
        return content

    def load(self) -> str:
        # SHA256SUMS es el último archivo que publica el pipeline: marca una release completa.
        with self._open_container() as container:
            sums = self._download(container, "SHA256SUMS", 4096).decode("utf-8")
            checksums: dict[str, str] = {}
            for line in sums.splitlines():
                parts = line.split()
                if (
                    len(parts) != 2
                    or not re.fullmatch(r"[a-f0-9]{64}", parts[0])
                    or parts[1] not in {"embed.html", "manifest.json"}
                    or parts[1] in checksums
                ):
                    raise InvalidEmbedRelease("SHA256SUMS inválido")
                checksums[parts[1]] = parts[0]
            if set(checksums) != {"embed.html", "manifest.json"}:
                raise InvalidEmbedRelease("SHA256SUMS incompleto")

            manifest_bytes = self._download(container, "manifest.json", 64 * 1024)
            if hashlib.sha256(manifest_bytes).hexdigest() != checksums["manifest.json"]:
                raise InvalidEmbedRelease("El manifiesto no coincide con SHA256SUMS")
            manifest = json.loads(manifest_bytes)
            if (
                not isinstance(manifest, dict)
                or type(manifest.get("schemaVersion")) is not int
                or manifest["schemaVersion"] != 1
                or manifest.get("commit") != self._settings.release_sha
                or manifest.get("template") != "embed.html"
                or not isinstance(manifest.get("modules"), list)
                or not all(isinstance(module, str) for module in manifest["modules"])
                or set(manifest["modules"]) != MODULOS_EMBED
            ):
                raise InvalidEmbedRelease("El manifiesto no describe la release configurada")

            html_bytes = self._download(container, "embed.html", self._settings.max_template_bytes)
            digest = hashlib.sha256(html_bytes).hexdigest()
            if (
                digest != checksums["embed.html"]
                or digest != manifest.get("sha256")
                or type(manifest.get("bytes")) is not int
                or manifest["bytes"] != len(html_bytes)
            ):
                raise InvalidEmbedRelease("El HTML no coincide con el manifiesto")

        template = html_bytes.decode("utf-8")
        if template.count(MARCADOR_MODULO) != 1 or template.count(MARCADOR_DATOS) != 1:
            raise InvalidEmbedRelease("El HTML no contiene los marcadores de inyección esperados")
        return template
