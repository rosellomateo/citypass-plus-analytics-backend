import json
from contextlib import nullcontext
from unittest.mock import Mock

import jwt
import pytest
from azure.core.exceptions import AzureError, ResourceNotFoundError
from fastapi.testclient import TestClient

from app.core.config import CorsSettings
from app.core.security.dependencies import obtener_validador
from app.main import create_app
from app.routers import rout_parte2
from app.schemas.sch_usuario_autenticado import UsuarioAutenticado

AREAS = ["claims", "emergencies", "mobility", "culture", "waste", "eda"]
HEADERS = {"Authorization": "Bearer synthetic-test", "Origin": "https://frontend.test"}


def missing_blob():
    error = ResourceNotFoundError("private storage detail")
    error.error_code = "BlobNotFound"
    return error


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_URL", "https://storage.test")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "gold")
    monkeypatch.setenv("AZURE_STORAGE_SAS_TOKEN", "synthetic-sas")
    monkeypatch.delenv("PART2_EVENTS_URL", raising=False)
    monkeypatch.delenv("PART2_EVENTS_BLOB", raising=False)
    storage = Mock()
    files = {}

    def download(path):
        if path not in files:
            raise missing_blob()
        return json.dumps(files[path]).encode()

    storage.download_blob.side_effect = download
    monkeypatch.setattr(rout_parte2, "AzureBlobStorage", lambda settings: nullcontext(storage))
    validator = Mock()
    validator.validar.return_value = UsuarioAutenticado(
        sub="test", groups=["admin"], module="analitica"
    )
    application = create_app(CorsSettings(("https://frontend.test",)))
    application.dependency_overrides[obtener_validador] = lambda: validator
    with TestClient(application) as client:
        yield client, storage, files, validator


@pytest.mark.parametrize("area", AREAS)
def test_part2_endpoint_returns_published_json_with_existing_admin_policy(setup, area):
    client, _, files, _ = setup
    metric_id = "received" if area == "eda" else "c1"
    files[f"parte2/{area}.json"] = {
        "fecha_snapshot": "2026-11-16",
        "version_cultura": 2 if area == "culture" else None,
        "datos": [{"id": metric_id, "etiqueta": "Indicador publicado", "valor": 7}],
    }
    response = client.get(f"/analytics/{area}/parte2", headers=HEADERS)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["access-control-allow-origin"] == "https://frontend.test"
    assert response.json()["datos"][0]["valor"] == 7
    assert response.json()["fecha_snapshot"] == "2026-11-16"


@pytest.mark.parametrize("area", AREAS)
@pytest.mark.parametrize("auth", ["missing", "invalid", "non-admin"])
def test_part2_authentication_and_permissions_run_before_reading_gold(setup, area, auth):
    client, storage, _, validator = setup
    headers = HEADERS if auth != "missing" else {}
    expected = 401
    if auth == "invalid":
        validator.validar.side_effect = jwt.InvalidTokenError()
    elif auth == "non-admin":
        validator.validar.return_value = UsuarioAutenticado(
            sub="test", groups=[], module="analitica"
        )
        expected = 403
    assert client.get(f"/analytics/{area}/parte2", headers=headers).status_code == expected
    storage.download_blob.assert_not_called()


@pytest.mark.parametrize("area", ["culture", "mobility", "waste", "eda"])
def test_missing_unavailable_metrics_return_empty_without_fabricating_zeroes(setup, area):
    client, storage, _, _ = setup
    response = client.get(f"/analytics/{area}/parte2", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["datos"] == []
    assert response.json()["fecha_snapshot"] is None
    assert all(call.args[0].endswith(".json") for call in storage.download_blob.call_args_list)


@pytest.mark.parametrize(
    "payload",
    [
        {"datos": [{"id": "c1", "valor": 1}, {"id": "c1", "valor": 2}]},
        {"datos": [{"id": "c1", "valor": float("nan")}]},
        {"datos": [{"id": "c1", "valor": float("inf")}]},
        {"datos": [{"id": "", "valor": 1}]},
        {"datos": "invalid"},
    ],
)
def test_invalid_published_data_is_a_generic_non_cached_503(setup, payload):
    client, _, files, _ = setup
    files["parte2/mobility.json"] = payload
    response = client.get("/analytics/mobility/parte2", headers=HEADERS)
    assert response.status_code == 503
    assert response.json() == {"detail": "No se pudieron consultar los indicadores"}
    assert response.headers["cache-control"] == "private, no-store"


def test_storage_failure_is_not_treated_as_an_empty_dataset(setup):
    client, storage, _, _ = setup
    storage.download_blob.side_effect = AzureError("private-sas-and-storage-details")
    response = client.get("/analytics/mobility/parte2", headers=HEADERS)
    assert response.status_code == 503
    assert "private-sas" not in response.text


def test_old_culture_contract_is_not_rendered_as_current_activity_metrics(setup):
    client, _, files, _ = setup
    files["parte2/culture.json"] = {"datos": [{"id": "c1", "valor": 90}]}
    response = client.get("/analytics/culture/parte2", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["datos"] == []


def test_main_registers_part2_in_openapi(setup):
    client, _, _, _ = setup
    paths = client.get("/openapi.json").json()["paths"]
    assert "/analytics/{area}/parte2" in paths
