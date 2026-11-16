"""Tableros autocontenidos: plantilla versionada + respuesta existente de analítica."""

import json
import time
from collections.abc import Callable
from contextlib import contextmanager
from threading import Lock
from typing import Any

from app.core.conexion import obtener_repositorio, obtener_repositorio_informes
from app.core.config import EmbedSettings
from app.repositories.embed_template_repository import (
    MARCADOR_DATOS,
    MARCADOR_MODULO,
    MODULOS_EMBED,
    EmbedTemplateRepository,
    InvalidEmbedRelease,
)
from app.services.espacios_cultura_service import obtener_analitica_espacios
from app.services.identidad_service import obtener_analitica_identidad
from app.services.movilidad_service import obtener_analitica_viajes
from app.services.reclamos_service import obtener_analitica_reclamos
from app.services.residuos_service import obtener_analitica_residuos
from app.services.seguridad_emergencias_service import obtener_analitica_emergencias

SERVICIOS = {
    "reclamos": obtener_analitica_reclamos,
    "emergencias": obtener_analitica_emergencias,
    "movilidad": obtener_analitica_viajes,
    "espacios": obtener_analitica_espacios,
    "residuos": obtener_analitica_residuos,
    "identidad": obtener_analitica_identidad,
}


def cargar_payload(modulo: str) -> dict[str, Any]:
    # Crear/cerrar los repositorios solo en un cache miss, después de autorizar al usuario.
    with (
        contextmanager(obtener_repositorio)() as gold,
        contextmanager(obtener_repositorio_informes)() as informes,
    ):
        return SERVICIOS[modulo](gold, informes).model_dump(mode="json")


class EmbedUnavailableError(RuntimeError):
    """No se pudo obtener una plantilla o datos válidos para el tablero."""


class EmbedService:
    def __init__(
        self,
        settings: EmbedSettings,
        templates: EmbedTemplateRepository,
        payload_loader: Callable[[str], dict[str, Any]] = cargar_payload,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._templates = templates
        self._payload_loader = payload_loader
        self._clock = clock
        self._template: str | None = None
        self._cache: dict[str, tuple[float, str]] = {}
        self._lock = Lock()

    def render(self, modulo: str) -> str:
        if modulo not in MODULOS_EMBED:
            raise ValueError("Módulo sin tablero embebido")
        # Evita múltiples descargas simultáneas al iniciar o vencer la caché.
        with self._lock:
            cached = self._cache.get(modulo)
            if cached and self._clock() - cached[0] < self._settings.cache_ttl_seconds:
                return cached[1]
            try:
                if self._template is None:
                    self._template = self._templates.load()
                if not self._templates.supports_module(modulo):
                    raise InvalidEmbedRelease("La release configurada no incluye este módulo")
                payload = self._payload_loader(modulo)
                # Los datos son JSON inerte. Escapar '<' impide cerrar el bloque script.
                data = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace(
                    "<", "\\u003c"
                )
                html = self._template.replace(MARCADOR_MODULO, modulo, 1).replace(
                    MARCADOR_DATOS, data, 1
                )
            except Exception as error:
                raise EmbedUnavailableError("Analítica no disponible") from error
            self._cache[modulo] = (self._clock(), html)
            return html
