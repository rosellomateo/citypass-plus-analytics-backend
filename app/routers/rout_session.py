from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.core.security.dependencies import obtener_usuario_actual
from app.core.security.permissions import allowed_dashboards
from app.schemas.sch_usuario_autenticado import UsuarioAutenticado

router = APIRouter(tags=["Sesion"])


class AnalyticsSession(BaseModel):
    preferred_username: str
    module: str
    groups: list[str]
    dashboards: list[str]
    initial_dashboard: str | None
    expires_at: int


@router.get("/auth/session")
def session(
    usuario: Annotated[UsuarioAutenticado, Depends(obtener_usuario_actual)],
    response: Response,
) -> AnalyticsSession:
    expires_at = usuario.expires_at
    if expires_at is None:
        raise HTTPException(
            status_code=401,
            detail="Token sin vencimiento",
            headers={"WWW-Authenticate": "Bearer"},
        )

    dashboards = allowed_dashboards(usuario.module, usuario.groups)
    response.headers["Cache-Control"] = "no-store"
    return AnalyticsSession(
        preferred_username=usuario.username or usuario.sub,
        module=usuario.module,
        groups=usuario.groups,
        dashboards=dashboards,
        initial_dashboard=dashboards[0] if dashboards else None,
        expires_at=expires_at,
    )
