from datetime import UTC, datetime

import polars as pl
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.conexion import obtener_repositorio


class FakeParquetRepository:
    def __init__(self):
        self.data = {
            "Reclamos/reclamos_resumen.parquet": pl.DataFrame(
                [
                    {
                        "barrio": "Palermo",
                        "categoria": "Alumbrado",
                        "prioridad": "Alta",
                        "origenClasificacion": "Manual",
                        "estado_actual": "Resuelto",
                        "row_count": 15,
                        "tiempo_prom_hasta_estado_actual": 24.5,
                        "fecha_snapshot": datetime(2026, 9, 21, 10, 30),
                    }
                ]
            ),
            "Emergencias y Seguridad/emergencias_resumen.parquet": pl.DataFrame(
                [
                    {
                        "estado_actual": "Resuelta",
                        "prioridad": "Alta",
                        "cantidadEmergencias": 12,
                        "tiempoPromRespuestaDespacho": 4.5,
                        "tiempoPromRespuestaLugar": 9.8,
                        "fecha_snapshot": datetime(2026, 9, 21, 10, 30),
                    }
                ]
            ),
            "Movilidad Urbana/viajes_resumen.parquet": pl.DataFrame(
                [
                    {
                        "fechaInicio": datetime(2026, 9, 21, 10, 30),
                        "estacionInicio": "Estación Central",
                        "duracionViaje": "15 minutos",
                        "cantidadViajes": 10,
                        "duracionTotalViajes": 150.0,
                        "promDuracion": 15.0,
                        "fecha_snapshot": datetime(2026, 9, 21, 12, 0),
                    }
                ]
            ),
            "Espacios Publicos y Cultura/reservas_resumen.parquet": pl.DataFrame(
                [
                    {
                        "recursoId": "REC-001",
                        "tipoReserva": "Presencial",
                        "categoria": "Cultura",
                        "zona": "Centro",
                        "cupoMaximo": 100.0,
                        "cantidadTotal": 80,
                        "cantidadConfirmadas": 70,
                        "cantidadCanceladas": 10,
                        "inscriptos": 75,
                        "pctOcupacion": 75.0,
                        "fecha_snapshot": datetime(2026, 9, 21, 10, 30),
                    }
                ]
            ),
            "Gestion de Residuos Inteligente/alertas_resumen.parquet": pl.DataFrame(
                [
                    {
                        "zona": "Norte",
                        "tipoAlerta": "Contenedor lleno",
                        "prioridad": "Alta",
                        "rangoNivelLlenado": "80-100%",
                        "cantidadAlertas": 20,
                        "cantidadResueltas": 15,
                        "tiempoPromResolucion": 35.5,
                        "fecha_snapshot": datetime(2026, 9, 21, 10, 30),
                    }
                ]
            ),
        }

    def list_folders(self):
        return []

    def list_datasets(self, prefix=None):
        return []

    def read(self, blob_name):
        return self.data.get(blob_name, pl.DataFrame())


@pytest.fixture
def client():
    fake_repository = FakeParquetRepository()

    app.dependency_overrides[obtener_repositorio] = lambda: fake_repository

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            "/analytics/reclamos",
            [
                {
                    "barrio": "Palermo",
                    "categoria": "Alumbrado",
                    "prioridad": "Alta",
                    "origenClasificacion": "Manual",
                    "estado_actual": "Resuelto",
                    "row_count": 15,
                    "tiempo_prom_hasta_estado_actual": 24.5,
                    "fecha_snapshot": "2026-09-21T10:30:00",
                }
            ],
        ),
        (
            "/analytics/seguridad-emergencias",
            [
                {
                    "estado_actual": "Resuelta",
                    "prioridad": "Alta",
                    "cantidadEmergencias": 12,
                    "tiempoPromRespuestaDespacho": 4.5,
                    "tiempoPromRespuestaLugar": 9.8,
                    "fecha_snapshot": "2026-09-21T10:30:00",
                }
            ],
        ),
        (
            "/analytics/movilidad-urbana",
            [
                {
                    "fechaInicio": "2026-09-21T10:30:00",
                    "estacionInicio": "Estación Central",
                    "duracionViaje": "15 minutos",
                    "cantidadViajes": 10,
                    "duracionTotalViajes": 150.0,
                    "promDuracion": 15.0,
                    "fecha_snapshot": "2026-09-21T12:00:00",
                }
            ],
        ),
        (
            "/analytics/espacios-cultura",
            [
                {
                    "recursoId": "REC-001",
                    "tipoReserva": "Presencial",
                    "categoria": "Cultura",
                    "zona": "Centro",
                    "cupoMaximo": 100.0,
                    "cantidadTotal": 80,
                    "cantidadConfirmadas": 70,
                    "cantidadCanceladas": 10,
                    "inscriptos": 75,
                    "pctOcupacion": 75.0,
                    "fecha_snapshot": "2026-09-21T10:30:00",
                }
            ],
        ),
        (
            "/analytics/residuos",
            [
                {
                    "zona": "Norte",
                    "tipoAlerta": "Contenedor lleno",
                    "prioridad": "Alta",
                    "rangoNivelLlenado": "80-100%",
                    "cantidadAlertas": 20,
                    "cantidadResueltas": 15,
                    "tiempoPromResolucion": 35.5,
                    "fecha_snapshot": "2026-09-21T10:30:00",
                }
            ],
        ),
    ],
)
def test_analytics_returns_json(
    client: TestClient,
    path: str,
    expected: list[dict],
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
        ("/analytics/reclamos", "Reclamo"),
        ("/analytics/movilidad-urbana", "Movilidad"),
        ("/analytics/espacios-cultura", "EspacioCultura"),
        ("/analytics/residuos", "Residuo"),
        ("/analytics/seguridad-emergencias", "SeguridadEmergencia"),
    ],
)
def test_openapi_declares_response_contract(client: TestClient, path: str, schema: str) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"][path]["get"]
    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response_schema["type"] == "array"
    assert response_schema["items"]["$ref"] == f"#/components/schemas/{schema}"
