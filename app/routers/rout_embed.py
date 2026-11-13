import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.security.embed_auth import autorizar_embed

router = APIRouter(tags=["Embed"])
log = logging.getLogger(__name__)


@router.get("/embed/{modulo}")
def embed(
    modulo: str, response: Response, usuario: Annotated[dict, Depends(autorizar_embed)]
) -> dict[str, str]:
    """Prueba de autenticación de usuarios; todavía no entrega el tablero HTML."""
    response.headers["Cache-Control"] = "private, no-store"
    log.info(
        "embed modulo=%s usuario=%s namespace=%s jti=%s",
        modulo,
        usuario["sub"],
        usuario.get("namespace"),
        usuario["jti"],
    )
    return {"status": "ok"}
