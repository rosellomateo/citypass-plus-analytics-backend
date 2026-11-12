from datetime import datetime, timezone
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
    validator = embed_auth.ServiceJWTValidator(SecuritySettings('https://idp.citypass.local', 'citypass', 'https://test/jwks'))
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    jwk['kid'] = 'test'
    validator._jwks_client.fetch_data = Mock(return_value={'keys': [jwk]})
    monkeypatch.setattr(embed_auth, 'obtener_validador_servicio', lambda: validator)
    def headers(module='emergencias', changes=None, missing=None, bad_signature=False):
        now = int(datetime.now(timezone.utc).timestamp())
        claims = dict(iss='https://idp.citypass.local', aud=['citypass'], sub='grupo5',
                      iat=now, exp=now+900, jti='test-id', token_use='service', ver=1,
                      namespace=embed_auth.NAMESPACES_POR_MODULO[module])
        claims.update(changes or {})
        if missing:
            del claims[missing]
        signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048) if bad_signature else key
        return {'Authorization': 'Bearer ' + jwt.encode(claims, signing_key, algorithm='RS256', headers={'kid':'test'})}
    with TestClient(create_app()) as client:
        yield client, headers, validator


@pytest.mark.parametrize('module', sorted(embed_auth.NAMESPACES_POR_MODULO))
def test_service_ok_without_human_or_storage(setup, module, monkeypatch):
    client, headers, _ = setup
    monkeypatch.delenv('EMBED_PLANTILLA', raising=False)
    r = client.get('/embed/'+module, headers=headers(module))
    assert r.status_code == 200
    assert r.json() == {'status':'ok'}
    assert r.headers['cache-control'] == 'private, no-store'


@pytest.mark.parametrize('changes', [
    {'aud':'citypass'}, {'aud':['citypass-analitica-api']}, {'aud':[]},
    {'aud':['citypass', 1]}, {'token_use':'human'}, {'ver':True}, {'ver':2},
    {'iss':'https://otro'}, {'exp':1}, {'sub':''}, {'namespace':[]}, {'jti':''},
    {'iat':9999999999}, {'exp':'9999999999'},
])
def test_invalid_token(setup, changes):
    client, headers, _ = setup
    assert client.get('/embed/emergencias', headers=headers(changes=changes)).status_code == 401


@pytest.mark.parametrize('claim', ['iss','aud','sub','iat','exp','jti','token_use','ver','namespace'])
def test_missing_claim(setup, claim):
    client, headers, _ = setup
    assert client.get('/embed/emergencias', headers=headers(missing=claim)).status_code == 401


@pytest.mark.parametrize('requested', sorted(embed_auth.NAMESPACES_POR_MODULO))
@pytest.mark.parametrize('caller', sorted(embed_auth.NAMESPACES_POR_MODULO))
def test_namespace_bound_to_route(setup, requested, caller):
    client, headers, _ = setup
    r = client.get('/embed/'+requested, headers=headers(caller))
    assert r.status_code == (200 if caller == requested else 403)


def test_bad_signature(setup):
    client, headers, _ = setup
    assert client.get('/embed/emergencias', headers=headers(bad_signature=True)).status_code == 401


def test_missing_token(setup):
    client, _, _ = setup
    assert client.get('/embed/emergencias').status_code == 401


def test_unknown_module(setup):
    client, headers, _ = setup
    assert client.get('/embed/analitica', headers=headers()).status_code == 404


def test_jwks_unavailable(setup):
    client, headers, validator = setup
    validator._jwks_client.fetch_data.side_effect = PyJWKClientConnectionError('offline')
    assert client.get('/embed/emergencias', headers=headers()).status_code == 503


def test_multiple_audiences_include_citypass(setup):
    client, headers, _ = setup
    assert client.get('/embed/emergencias', headers=headers(changes={'aud':['otra','citypass']})).status_code == 200


def test_service_rejected_by_analytics(setup, monkeypatch):
    from app.core.security.dependencies import obtener_validador
    from app.core.security.jwt_validator import JWTValidator
    client, headers, service = setup
    human = JWTValidator(SecuritySettings('https://idp.citypass.local', 'citypass-analitica-api', 'https://test/jwks'))
    human._jwks_client = service._jwks_client
    client.app.dependency_overrides[obtener_validador] = lambda: human
    try:
        r = client.get('/analytics/seguridad-emergencias', headers=headers(changes={'aud':'citypass-analitica-api','groups':['admin'],'module':'emergencias'}))
        assert r.status_code == 401
    finally:
        client.app.dependency_overrides.clear()
