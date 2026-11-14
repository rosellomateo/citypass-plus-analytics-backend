from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWKClientConnectionError

from app.core.config import SecuritySettings
from app.core.security.jwt_validator import JWTValidator
from app.core.security.permissions import allowed_dashboards
from app.schemas.sch_usuario_autenticado import UsuarioAutenticado

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def obtener_validador() -> JWTValidator:
    try:
        return JWTValidator(SecuritySettings.from_environment())
    except (ValueError, RuntimeError):
        raise HTTPException(503, "Autenticación no configurada") from None


def require_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            401, "Token de autenticación requerido", headers={"WWW-Authenticate": "Bearer"}
        )
    return credentials.credentials


def obtener_usuario_actual(
    token: Annotated[str, Depends(require_token)],
    validator: Annotated[JWTValidator, Depends(obtener_validador)],
) -> UsuarioAutenticado:
    try:
        return validator.validar(token)
    except PyJWKClientConnectionError:
        raise HTTPException(503, "No se pudo consultar el JWKS") from None
    except jwt.PyJWTError:
        raise HTTPException(
            401, "Token inválido o expirado", headers={"WWW-Authenticate": "Bearer"}
        ) from None


def require_dashboard(area: str) -> Callable:
    def check(usuario: Annotated[UsuarioAutenticado, Depends(obtener_usuario_actual)]) -> None:
        require_area(area, usuario)

    return check


def require_area(
    area: str,
    usuario: UsuarioAutenticado,
) -> None:
    if area not in allowed_dashboards(usuario.module, usuario.groups):
        raise HTTPException(403, "No tenés permiso para este tablero")
