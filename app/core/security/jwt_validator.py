import jwt
from jwt import PyJWKClient

from app.core.config import SecuritySettings
from app.core.security.permissions import canonical_module, module_audiences
from app.schemas.sch_usuario_autenticado import UsuarioAutenticado


class JWTValidator:
    def __init__(self, settings: SecuritySettings) -> None:
        self._settings = settings
        self._jwks_client = PyJWKClient(
            uri=settings.jwks_url,
            headers={"User-Agent": "CityPass-Analytics/1.0"},
            cache_jwk_set=True,
            lifespan=300,
            timeout=5,
        )

    def validar(self, token: str) -> UsuarioAutenticado:
        signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        audiences = module_audiences(self._settings.audience)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=self._settings.issuer,
            audience=set().union(*audiences.values()),
            options={
                "require": ["iss", "sub", "aud", "exp", "token_use", "ver", "groups", "module"]
            },
        )

        if claims["token_use"] != "human" or type(claims["ver"]) is not int or claims["ver"] != 1:
            raise jwt.InvalidTokenError("Tipo o versión de token inválidos")

        module = claims["module"]
        if not isinstance(module, str) or not module.strip():
            raise jwt.InvalidTokenError("El claim module debe ser un string no vacío")
        module = canonical_module(module)

        audience = claims["aud"]
        values = [audience] if isinstance(audience, str) else audience
        if not set(values).intersection(audiences.get(module, set())):
            raise jwt.InvalidTokenError("Audience no permitida para el módulo")

        sub = claims["sub"]
        if not isinstance(sub, str) or not sub.strip():
            raise jwt.InvalidTokenError("Identificador de usuario inválido")

        groups = claims["groups"]
        if not isinstance(groups, list) or not all(
            isinstance(group, str) and group.strip() for group in groups
        ):
            raise jwt.InvalidTokenError("El claim groups debe ser una lista de strings")

        if type(claims["exp"]) is not int:
            raise jwt.InvalidTokenError("Vencimiento inválido")

        username = claims.get("preferred_username")
        jti = claims.get("jti")
        return UsuarioAutenticado(
            sub=sub,
            username=username if isinstance(username, str) else None,
            groups=groups,
            module=module,
            jti=jti if isinstance(jti, str) else None,
            expires_at=claims["exp"],
        )
