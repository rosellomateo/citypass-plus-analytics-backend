import jwt
from jwt import PyJWKClient

from app.core.config import SecuritySettings
from app.schemas.sch_usuario_autenticado import UsuarioAutenticado


class JWTValidator:
    def __init__(self, settings: SecuritySettings) -> None:
        self._settings = settings

        # Cliente para obtener las claves públicas del IdP.
        # Mantiene una caché del JWKS.
        self._jwks_client = PyJWKClient(
            uri=settings.jwks_url,
            headers={"User-Agent": "CityPass-Analytics/1.0"},
            cache_jwk_set=True,
            lifespan=300,
            timeout=5,
        )

    def validar(self, token: str) -> UsuarioAutenticado:
        # 1. Buscar la clave pública correspondiente al kid.
        signing_key = self._jwks_client.get_signing_key_from_jwt(token)

        # 2. Verificar firma RS256 y claims estándar.
        claims = jwt.decode(
            jwt=token,
            key=signing_key.key,
            algorithms=["RS256"],
            issuer=self._settings.issuer,
            audience=self._settings.audience,
            leeway=60,
            options={
                "require": [
                    "iss",
                    "sub",
                    "aud",
                    "exp",
                    "token_use",
                    "ver",
                    "groups",
                    "module",
                ],
            },
        )

        # 3. Validaciones específicas del contrato.
        if claims.get("token_use") != "human":
            raise jwt.InvalidTokenError("Tipo de token no permitido")

        if type(claims.get("ver")) is not int or claims["ver"] != 1:
            raise jwt.InvalidTokenError("Versión del contrato inválida")

        audience = claims.get("aud")

        # Formato actual de Identidad: aud es un string, no una lista.
        if not isinstance(audience, str) or not audience.strip():
            raise jwt.InvalidTokenError("El claim aud debe ser un string no vacío")

        if audience != self._settings.audience:
            raise jwt.InvalidTokenError("Audience no permitida")

        sub = claims.get("sub")

        if not isinstance(sub, str) or not sub.strip():
            raise jwt.InvalidTokenError("Identificador de usuario inválido")

        groups = claims.get("groups")

        if not isinstance(groups, list) or not all(isinstance(group, str) for group in groups):
            raise jwt.InvalidTokenError("El claim groups debe ser una lista de strings")

        module = claims.get("module")
        if not isinstance(module, str) or not module.strip():
            raise jwt.InvalidTokenError("El claim module debe ser un string no vacío")

        # 4. Construir el usuario autenticado.
        return UsuarioAutenticado(
            sub=sub,
            username=claims.get("preferred_username"),
            groups=groups,
            module=module,
            jti=claims.get("jti"),
        )
