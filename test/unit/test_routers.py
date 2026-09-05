from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    # Las respuestas temporales deben funcionar sin credenciales de Azure.
    for name in (
        "AZURE_STORAGE_ACCOUNT_URL",
        "AZURE_STORAGE_CONTAINER",
        "AZURE_STORAGE_SAS_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            "/analytics/reclamos",
            {
                "total_reclamos": 0,
                "tiempo_promedio_resolucion_horas": 0.0,
                "reclamos_por_categoria": [],
                "reclamos_por_estado": [],
                "tiempo_resolucion_categoria": [],
            },
        ),
        (
            "/analytics/seguridad-emergencias",
            {
                "total_emergencias": 0,
                "emergencias_activas": 0,
                "emergencias_cerradas": 0,
                "tiempo_promedio_despacho_minutos": 0.0,
                "emergencias_por_estado": [],
                "emergencias_por_prioridad": [],
                "despacho_por_prioridad": [],
            },
        ),
        (
            "/analytics/movilidad-urbana",
            {
                "total_viajes_iniciados": 0,
                "duracion_promedio_viaje_minutos": 0.0,
                "viajes_por_estacion_origen": [],
                "viajes_por_franja_horaria": [],
                "distribucion_duracion_viajes": [],
            },
        ),
        (
            "/analytics/espacios-cultura",
            {
                "reservas_confirmadas": 0,
                "reservas_canceladas": 0,
                "tasa_cancelacion_porcentaje": 0.0,
                "ocupacion_promedio_porcentaje": 0.0,
                "reservas_por_espacio": [],
                "inscripciones_por_categoria": [],
                "inscripciones_por_evento": [],
            },
        ),
        (
            "/analytics/residuos",
            {
                "total_recolectado_toneladas": 0.0,
                "cantidad_contenedores_criticos": 0,
                "tasa_recoleccion": 0.0,
                "tiempo_promedio_vaciado": 0.0,
                "contenedores_por_estado": [],
                "volumen_por_tipo_residuo": [],
                "tiempo_vaciado_por_zona": [],
                "detalle_contenedores_criticos": [],
            },
        ),
    ],
)
def test_analytics_returns_placeholder_json(
    client: TestClient, path: str, expected: dict
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == expected


def test_event_returns_serializable_utc_datetime(client: TestClient) -> None:
    response = client.get("/analytics/eventos")

    assert response.status_code == 200
    payload = response.json()
    occurred_at = datetime.fromisoformat(payload.pop("fecha_hora"))
    assert occurred_at == datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
    assert occurred_at.utcoffset().total_seconds() == 0
    assert payload == {
        "id_evento": "evento-prueba-001",
        "tipo_evento": "EmergenciaCreada",
        "area": "EMERGENCIAS",
        "version": "1.0",
        "id_correlacion": "correlacion-prueba-001",
    }


@pytest.mark.parametrize(
    ("path", "schema"),
    [
        ("/analytics/reclamos", "RespuestaAnaliticaReclamos"),
        ("/analytics/eventos", "RespuestaAnaliticaEventos"),
        ("/analytics/movilidad-urbana", "RespuestaAnaliticaMovilidad"),
        ("/analytics/espacios-cultura", "RespuestaAnaliticaEspaciosCultura"),
        ("/analytics/residuos", "RespuestaAnaliticaResiduos"),
        ("/analytics/seguridad-emergencias", "RespuestaAnaliticaSeguridadEmergencias"),
    ],
)
def test_openapi_declares_response_contract(
    client: TestClient, path: str, schema: str
) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"][path]["get"]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert response_schema["$ref"] == f"#/components/schemas/{schema}"
