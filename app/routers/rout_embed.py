import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.core.embed import obtener_servicio_embed
from app.core.security.embed_auth import autorizar_embed
from app.services.embed_service import EmbedUnavailableError

router = APIRouter(tags=["Embed"])
log = logging.getLogger(__name__)

CABECERAS = {
    "Cache-Control": "private, no-store",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
        "img-src data: https:; font-src data:"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


@router.get(
    "/embed/{modulo}",
    response_class=HTMLResponse,
    response_model=None,
    responses={
        200: {
            "description": "Tablero HTML con datos e informe del módulo",
        },
        401: {"description": "Token ausente o inválido"},
        403: {"description": "Namespace no autorizado"},
        404: {"description": "Módulo desconocido"},
        503: {"description": "Autenticación, plantilla o datos no disponibles"},
    },
)
def embed(modulo: str, usuario: Annotated[dict, Depends(autorizar_embed)]) -> HTMLResponse:
    """Autoriza cada request y entrega el tablero del módulo con datos incluidos."""
    try:
        html = obtener_servicio_embed().render(modulo)
    except EmbedUnavailableError as error:
        # No registrar URLs de Storage, credenciales ni datos de los usuarios.
        log.error("embed no disponible modulo=%s causa=%s", modulo, type(error.__cause__).__name__)
        raise HTTPException(503, "Analítica no disponible", headers=CABECERAS) from None
    response = HTMLResponse(html, headers=CABECERAS)

    log.info(
        "embed modulo=%s usuario=%s namespace=%s jti=%s",
        modulo,
        usuario["sub"],
        usuario.get("namespace"),
        usuario["jti"],
    )
    return response
