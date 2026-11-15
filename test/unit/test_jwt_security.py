from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.core.config import CorsSettings, SecuritySettings
from app.core.security.dependencies import obtener_validador
from app.core.security.jwt_validator import JWTValidator
from app.main import create_app


@pytest.fixture
def signed_token():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    claims = {
        "sub": "usuario-prueba",
        "iss": "https://identidad.test",
        "aud": "analytics",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "token_use": "human",
        "ver": 1,
        "groups": [],
        "module": "reclamos",
    }
    validator = JWTValidator(
        SecuritySettings(
            issuer="https://identidad.test",
            audience="analytics",
            jwks_url="https://api.citypass-login.pp.ua/.well-known/jwks.json",
        )
    )
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    jwk["kid"] = "clave-prueba"
    validator._jwks_client.fetch_data = Mock(return_value={"keys": [jwk]})
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "clave-prueba"})
    return validator, token, key, claims


def test_real_signature_and_claims(signed_token):
    validator, token, _, _ = signed_token
    assert validator.validar(token).sub == "usuario-prueba"


@pytest.mark.parametrize(
    "claim,value",
    [
        ("iss", "https://otro.test"),
        ("aud", "otra-api"),
        ("aud", ["analytics"]),
        ("aud", []),
        ("aud", ""),
        ("aud", 123),
        ("aud", "analytics-extra"),
        ("exp", 1),
        ("module", None),
        ("module", ""),
        ("module", " "),
        ("module", []),
        ("module", 123),
    ],
)
def test_rejects_invalid_claims(signed_token, claim, value):
    validator, _, key, claims = signed_token
    claims[claim] = value
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "clave-prueba"})
    with pytest.raises(jwt.InvalidTokenError):
        validator.validar(token)


def test_rejects_invalid_signature(signed_token):
    validator, _, _, claims = signed_token
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(claims, other_key, algorithm="RS256", headers={"kid": "clave-prueba"})
    with pytest.raises(jwt.InvalidSignatureError):
        validator.validar(token)


def test_each_request_validates_token(signed_token):
    validator, token, _, _ = signed_token
    validator.validar = Mock(wraps=validator.validar)
    app = create_app()
    app.dependency_overrides[obtener_validador] = lambda: validator
    from app.core.conexion import obtener_repositorio, obtener_repositorio_informes
    from test.unit.test_routers import FakeJsonRepository, FakeParquetRepository

    app.dependency_overrides[obtener_repositorio] = FakeParquetRepository
    app.dependency_overrides[obtener_repositorio_informes] = FakeJsonRepository
    with TestClient(app) as client:
        for _ in range(2):
            response = client.get(
                "/analytics/reclamos",
                headers={
                    "Authorization": f"Bearer {token}",
                },
            )
            # El token se valida, pero sin admin se rechaza el acceso.
            assert response.status_code == 403
    assert validator.validar.call_count == 2


def test_jwks_default(monkeypatch):
    monkeypatch.setenv("JWT_ISSUER", "https://identidad.test")
    monkeypatch.setenv("JWT_AUDIENCE", "analytics")
    monkeypatch.setenv("JWKS_URL", "")
    assert SecuritySettings.from_environment().jwks_url == (
        "https://api.citypass-login.pp.ua/.well-known/jwks.json"
    )


def test_cors_accepts_authorization():
    app = create_app(CorsSettings(allowed_origins=("http://localhost:5173",)))
    with TestClient(app) as client:
        response = client.options(
            "/analytics/reclamos",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
    assert response.status_code == 200


def test_requires_module_claim(signed_token):
    validator, _, key, claims = signed_token
    del claims["module"]
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "clave-prueba"})
    with pytest.raises(jwt.MissingRequiredClaimError):
        validator.validar(token)


def test_preserves_module_claim(signed_token):
    validator, token, _, _ = signed_token
    assert validator.validar(token).module == "reclamos"


@pytest.mark.parametrize(
    "audience,groups,expected",
    [
        ("citypass-analitica-api", ["admin"], 200),
        ("citypass-analitica-api", ["delegados", "admin"], 200),
        ("citypass-analitica-api", ["reclamos"], 403),
        ("citypass-analitica-api", ["Admin"], 403),
        ("citypass-analitica-api", [], 403),
        ("citypass-reclamos-api", ["admin"], 401),
        ("citypass-admin-api", ["admin"], 401),
    ],
)
def test_analytics_admin_and_audience(signed_token, audience, groups, expected):
    from app.core.conexion import obtener_repositorio, obtener_repositorio_informes
    from test.unit.test_routers import FakeJsonRepository, FakeParquetRepository

    validator, _, key, claims = signed_token
    validator._settings = SecuritySettings(
        issuer="https://identidad.test",
        audience="citypass-analitica-api",
        jwks_url="https://api.citypass-login.pp.ua/.well-known/jwks.json",
    )
    claims.update(aud=audience, groups=groups, module="analitica")
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "clave-prueba"})
    app = create_app()
    app.dependency_overrides[obtener_validador] = lambda: validator
    app.dependency_overrides[obtener_repositorio] = FakeParquetRepository
    app.dependency_overrides[obtener_repositorio_informes] = FakeJsonRepository
    with TestClient(app) as client:
        for path in [
            "identidad",
            "reclamos",
            "residuos",
            "movilidad-urbana",
            "espacios-cultura",
            "seguridad-emergencias",
        ]:
            response = client.get(
                "/analytics/" + path, headers={"Authorization": "Bearer " + token}
            )
            assert response.status_code == expected
