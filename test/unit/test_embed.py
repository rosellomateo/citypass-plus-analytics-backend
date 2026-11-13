from datetime import UTC, datetime
from unittest.mock import Mock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.exceptions import PyJWKClientConnectionError

from app.core.config import SecuritySettings
from app.core.security import embed_auth
from app.main import create_app


@pytest.fixture
def setup(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    validator = embed_auth.HumanEmbedJWTValidator(
        SecuritySettings(
            "https://idp.citypass.local", "citypass-emergencias-api", "https://test/jwks"
        )
    )
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    jwk["kid"] = "test"
    validator._jwks_client.fetch_data = Mock(return_value={"keys": [jwk]})

    def get_validator(module):
        scoped = embed_auth.HumanEmbedJWTValidator(
            SecuritySettings(
                "https://idp.citypass.local",
                embed_auth.AUDIENCIAS_POR_MODULO[module],
                "https://test/jwks",
            )
        )
        scoped._jwks_client = validator._jwks_client
        return scoped

    monkeypatch.setattr(embed_auth, "obtener_validador_embed", get_validator)

    def headers(module="emergencias", changes=None, missing=None, bad_signature=False):
        now = int(datetime.now(UTC).timestamp())
        claims = dict(
            iss="https://idp.citypass.local",
            aud=embed_auth.AUDIENCIAS_POR_MODULO[module],
            sub="U000012",
            iat=now,
            exp=now + 900,
            jti="test-id",
            token_use="human",
            ver=1,
            namespace=embed_auth.NAMESPACES_POR_MODULO[module],
        )
        claims.update(changes or {})
        if missing:
            del claims[missing]
        signing_key = (
            rsa.generate_private_key(public_exponent=65537, key_size=2048) if bad_signature else key
        )
        return {
            "Authorization": "Bearer "
            + jwt.encode(claims, signing_key, algorithm="RS256", headers={"kid": "test"})
        }

    with TestClient(create_app()) as client:
        yield client, headers, validator


@pytest.mark.parametrize("module", sorted(embed_auth.NAMESPACES_POR_MODULO))
def test_human_ok_without_groups_module_or_storage(setup, module, monkeypatch):
    client, headers, _ = setup
    monkeypatch.delenv("EMBED_PLANTILLA", raising=False)
    r = client.get("/embed/" + module, headers=headers(module))
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize(
    "changes",
    [
        {"aud": "citypass"},
        {"aud": ["citypass-analitica-api"]},
        {"aud": []},
        {"aud": ["citypass", 1]},
        {"token_use": "service"},
        {"ver": True},
        {"ver": 2},
        {"iss": "https://otro"},
        {"exp": 1},
        {"sub": ""},
        {"namespace": []},
        {"jti": ""},
        {"iat": 9999999999},
        {"exp": "9999999999"},
    ],
)
def test_invalid_token(setup, changes):
    client, headers, _ = setup
    assert client.get("/embed/emergencias", headers=headers(changes=changes)).status_code == 401


@pytest.mark.parametrize(
    "claim", ["iss", "aud", "sub", "iat", "exp", "jti", "token_use", "ver", "namespace"]
)
def test_missing_claim(setup, claim):
    client, headers, _ = setup
    assert client.get("/embed/emergencias", headers=headers(missing=claim)).status_code == 401


@pytest.mark.parametrize("requested", sorted(embed_auth.NAMESPACES_POR_MODULO))
@pytest.mark.parametrize("caller", sorted(embed_auth.NAMESPACES_POR_MODULO))
def test_namespace_bound_to_route(setup, requested, caller):
    client, headers, _ = setup
    r = client.get(
        "/embed/" + requested,
        headers=headers(requested, changes={"namespace": embed_auth.NAMESPACES_POR_MODULO[caller]}),
    )
    assert r.status_code == (200 if caller == requested else 403)


def test_bad_signature(setup):
    client, headers, _ = setup
    assert client.get("/embed/emergencias", headers=headers(bad_signature=True)).status_code == 401


def test_missing_token(setup):
    client, _, _ = setup
    assert client.get("/embed/emergencias").status_code == 401


def test_unknown_module(setup):
    client, headers, _ = setup
    assert client.get("/embed/analitica", headers=headers()).status_code == 404


def test_jwks_unavailable(setup):
    client, headers, validator = setup
    validator._jwks_client.fetch_data.side_effect = PyJWKClientConnectionError("offline")
    assert client.get("/embed/emergencias", headers=headers()).status_code == 503


def test_array_audience_rejected(setup):
    client, headers, _ = setup
    assert (
        client.get(
            "/embed/emergencias",
            headers=headers(changes={"aud": ["otra", "citypass-emergencias-api"]}),
        ).status_code
        == 401
    )


def test_service_rejected_by_analytics(setup, monkeypatch):
    from app.core.security.dependencies import obtener_validador
    from app.core.security.jwt_validator import JWTValidator

    client, headers, service = setup
    human = JWTValidator(
        SecuritySettings(
            "https://idp.citypass.local", "citypass-analitica-api", "https://test/jwks"
        )
    )
    human._jwks_client = service._jwks_client
    client.app.dependency_overrides[obtener_validador] = lambda: human
    try:
        r = client.get(
            "/analytics/seguridad-emergencias",
            headers=headers(
                changes={
                    "aud": "citypass-analitica-api",
                    "groups": ["admin"],
                    "token_use": "service",
                    "module": "emergencias",
                }
            ),
        )
        assert r.status_code == 401
    finally:
        client.app.dependency_overrides.clear()


@pytest.mark.parametrize("requested", sorted(embed_auth.NAMESPACES_POR_MODULO))
@pytest.mark.parametrize("caller", sorted(embed_auth.NAMESPACES_POR_MODULO))
def test_audience_bound_to_route(setup, requested, caller):
    client, headers, _ = setup
    response = client.get(
        "/embed/" + requested,
        headers=headers(requested, changes={"aud": embed_auth.AUDIENCIAS_POR_MODULO[caller]}),
    )
    assert response.status_code == (200 if caller == requested else 401)


def test_admin_does_not_bypass_namespace(setup):
    client, headers, _ = setup
    response = client.get(
        "/embed/emergencias",
        headers=headers(
            changes={
                "namespace": "com.citypass.analitica",
                "groups": ["admin"],
                "module": "analitica",
            }
        ),
    )
    assert response.status_code == 403
