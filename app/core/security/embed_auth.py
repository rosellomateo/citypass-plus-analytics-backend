"""Validación de servicios para la etapa de prueba de embed."""
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jwt.exceptions import PyJWKClientConnectionError

from app.core.config import SecuritySettings
from app.core.security.dependencies import bearer_scheme
from app.core.security.jwt_validator import JWTValidator

NAMESPACES_POR_MODULO = {
    "reclamos": "com.citypass.reclamos",
    "residuos": "com.citypass.residuos",
    "movilidad": "com.citypass.movilidad",
    "emergencias": "com.citypass.emergencias",
    "espacios": "com.citypass.espacios",
}


class ServiceJWTValidator(JWTValidator):
    def validar_servicio(self, token: str) -> dict:
        key = self._jwks_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["RS256"], issuer=self._settings.issuer,
            audience="citypass", leeway=60,
            options={"require": ["iss", "aud", "sub", "iat", "exp", "jti",
                                 "token_use", "ver", "namespace"]},
        )
        if claims["token_use"] != "service":
            raise jwt.InvalidTokenError("Se requiere un token de servicio")
        if type(claims["ver"]) is not int or claims["ver"] != 1:
            raise jwt.InvalidTokenError("Versión inválida")
        aud = claims["aud"]
        if not isinstance(aud, list) or not all(isinstance(a, str) and a for a in aud) or "citypass" not in aud:
            raise jwt.InvalidTokenError("aud debe ser una lista que incluya citypass")
        for name in ("sub", "jti", "namespace"):
            if not isinstance(claims[name], str) or not claims[name].strip():
                raise jwt.InvalidTokenError(f"Claim {name} inválido")
        for name in ("iat", "exp"):
            if type(claims[name]) is not int:
                raise jwt.InvalidTokenError(f"Claim {name} inválido")
        return claims


@lru_cache
def obtener_validador_servicio() -> ServiceJWTValidator:
    try:
        base = SecuritySettings.from_environment()
        return ServiceJWTValidator(SecuritySettings(base.issuer, "citypass", base.jwks_url))
    except (ValueError, RuntimeError):
        raise HTTPException(503, "Autenticación embed no configurada") from None


def autorizar_embed(
    modulo: str,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    if modulo not in NAMESPACES_POR_MODULO:
        raise HTTPException(404, "Módulo desconocido")
    if credentials is None:
        raise HTTPException(401, "Se requiere el token de servicio",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = obtener_validador_servicio().validar_servicio(credentials.credentials)
    except PyJWKClientConnectionError:
        raise HTTPException(503, "No se pudo consultar el JWKS") from None
    except jwt.PyJWTError:
        raise HTTPException(401, "Token inválido o expirado",
                            headers={"WWW-Authenticate": "Bearer"}) from None
    if claims["namespace"] != NAMESPACES_POR_MODULO[modulo]:
        raise HTTPException(403, "El servicio no puede acceder a este módulo")
    return claims
