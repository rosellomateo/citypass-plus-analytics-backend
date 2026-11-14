from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.security.dependencies import obtener_usuario_actual
from app.core.security.permissions import allowed_dashboards
from app.schemas.sch_usuario_autenticado import UsuarioAutenticado

router = APIRouter(tags=["Sesión"])


@router.get("/auth/session")
def session(
    usuario: Annotated[UsuarioAutenticado, Depends(obtener_usuario_actual)],
    response: Response,
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return {
        "preferred_username": usuario.username or usuario.sub,
        "module": usuario.module,
        "groups": usuario.groups,
        "dashboards": allowed_dashboards(usuario.module, usuario.groups),
        "expires_at": usuario.expires_at,
    }
