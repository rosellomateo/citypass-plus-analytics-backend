from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt.exceptions import PyJWKClientError

from app.core.config import SecuritySettings
from app.core.security.jwt_validator import JWTValidator
from app.core.security.permissions import es_admin
from app.schemas.sch_usuario_autenticado import UsuarioAutenticado

# Extrae el Bearer Token del header Authorization.
bearer_scheme = HTTPBearer(auto_error=False)


# Reutilizamos el validador para aprovechar la caché JWKS.
@lru_cache
def obtener_validador() -> JWTValidator:
    settings = SecuritySettings.from_environment()
    return JWTValidator(settings)


# Dependencia de autenticación.
def obtener_usuario_actual(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    validator: Annotated[
        JWTValidator,
        Depends(obtener_validador),
    ],
) -> UsuarioAutenticado:

    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return validator.validar(credentials.credentials)

    except PyJWKClientError:
        # Un fallo al resolver JWKS no debe permitir el acceso.
        # Conviene distinguirlo de un JWT inválido en los logs.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo verificar el token",
        ) from None

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


# Todos los paneles de la web propia requieren el grupo admin.
def requerir_admin(
    usuario: Annotated[UsuarioAutenticado, Depends(obtener_usuario_actual)],
) -> UsuarioAutenticado:
    if not es_admin(usuario.groups):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere el grupo admin",
        )
    return usuario
