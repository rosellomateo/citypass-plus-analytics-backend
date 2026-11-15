from functools import lru_cache

from fastapi import HTTPException

from app.core.config import ConfigurationError, EmbedSettings
from app.repositories.embed_template_repository import EmbedTemplateRepository
from app.services.embed_service import EmbedService


@lru_cache(maxsize=1)
def obtener_servicio_embed() -> EmbedService:
    # La configuración es perezosa: /health y la autenticación funcionan sin una release.
    try:
        settings = EmbedSettings.from_environment()
    except ConfigurationError:
        raise HTTPException(
            503, "Entrega HTML embed no configurada", headers={"Cache-Control": "private, no-store"}
        ) from None
    return EmbedService(settings, EmbedTemplateRepository(settings))
