"""Validación de usuarios por namespace para la etapa de prueba de embed."""

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


AUDIENCIAS_POR_MODULO = {modulo: f"citypass-{modulo}-api" for modulo in NAMESPACES_POR_MODULO}


AUDIENCIA_ADMIN = "citypass-admin-api"


class HumanEmbedJWTValidator(JWTValidator):
    def validar_usuario(self, token: str) -> dict:
        audiencias_permitidas = (self._settings.audience, AUDIENCIA_ADMIN)
        key = self._jwks_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=self._settings.issuer,
            audience=audiencias_permitidas,
            leeway=60,
            options={
                "require": [
                    "iss",
                    "aud",
                    "sub",
                    "iat",
                    "exp",
                    "jti",
                    "token_use",
                    "ver",
                    "namespace",
                ]
            },
        )
        if claims["token_use"] != "human":
            raise jwt.InvalidTokenError("Se requiere un token de usuario human")
        if type(claims["ver"]) is not int or claims["ver"] != 1:
            raise jwt.InvalidTokenError("Versión inválida")
        aud = claims["aud"]
        if not isinstance(aud, str) or aud not in audiencias_permitidas:
            raise jwt.InvalidTokenError(
                "aud debe ser un string con la audiencia del módulo o de admin"
            )
        for name in ("sub", "jti", "namespace"):
            if not isinstance(claims[name], str) or not claims[name].strip():
                raise jwt.InvalidTokenError(f"Claim {name} inválido")
        for name in ("iat", "exp"):
            if type(claims[name]) is not int:
                raise jwt.InvalidTokenError(f"Claim {name} inválido")
        return claims


@lru_cache
def obtener_validador_embed(modulo: str) -> HumanEmbedJWTValidator:
    try:
        base = SecuritySettings.from_environment()
        return HumanEmbedJWTValidator(
            SecuritySettings(base.issuer, AUDIENCIAS_POR_MODULO[modulo], base.jwks_url)
        )
    except (ValueError, RuntimeError):
        raise HTTPException(503, "Autenticación embed no configurada") from None


def autorizar_embed(
    modulo: str,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    if modulo not in NAMESPACES_POR_MODULO:
        raise HTTPException(404, "Módulo desconocido")
    if credentials is None:
        raise HTTPException(
            401, "Se requiere el token de usuario human", headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        claims = obtener_validador_embed(modulo).validar_usuario(credentials.credentials)
    except PyJWKClientConnectionError:
        raise HTTPException(503, "No se pudo consultar el JWKS") from None
    except jwt.PyJWTError:
        raise HTTPException(
            401, "Token inválido o expirado", headers={"WWW-Authenticate": "Bearer"}
        ) from None
    if claims["namespace"] != NAMESPACES_POR_MODULO[modulo]:
        raise HTTPException(403, "El usuario no puede acceder a este módulo")
    return claims
