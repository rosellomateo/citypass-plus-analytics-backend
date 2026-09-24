from datetime import datetime

import polars as pl
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.conexion import obtener_repositorio, obtener_repositorio_informes


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


REPORT_FILES = {
    "/analytics/reclamos": "reclamos.json",
    "/analytics/seguridad-emergencias": "emergencias.json",
    "/analytics/movilidad-urbana": "movilidad.json",
    "/analytics/espacios-cultura": "espacios.json",
    "/analytics/residuos": "residuos.json",
}


def make_report(filename):
    return {
        "actualizado_en": "2026-09-21T12:00:00",
        "analisis": [
            {
                "generado_en": "2026-09-21T12:00:00",
                "semana": semana,
                "metadata": {"fuentes": [filename], "cifras": {"total": 12}},
                "resumen": {
                    "parrafo_ejecutivo": f"Análisis de {filename}",
                    "puntos_destacados": ["Mejora del servicio"],
                    "recomendaciones": [],
                    "riesgos": [],
                },
            }
            for semana in ["2026-W39", "2026-W38"]
        ],
        "caso_de_uso": filename,
        "semanas": ["2026-W39", "2026-W38"],
        "ultima_semana": "2026-W39",
        "version_esquema": "1.0",
    }


class FakeJsonRepository:
    def read(self, blob_name):
        assert blob_name in REPORT_FILES.values()
        return make_report(blob_name)


@pytest.fixture
def client():
    app.dependency_overrides[obtener_repositorio] = FakeParquetRepository
    app.dependency_overrides[obtener_repositorio_informes] = FakeJsonRepository
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
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
    payload = response.json()

    informe_esperado = make_report(REPORT_FILES[path])

    assert payload["datos"] == expected
    assert payload["informe"] == informe_esperado


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

    document = response.json()

    operation = document["paths"][path]["get"]
    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

    # Obtener la clase de respuesta referenciada por OpenAPI.
    response_name = response_schema["$ref"].rsplit("/", 1)[-1]
    properties = document["components"]["schemas"][response_name]["properties"]

    # "datos" sigue siendo una lista de entidades.
    assert properties["datos"]["type"] == "array"
    assert properties["datos"]["items"]["$ref"] == f"#/components/schemas/{schema}"

    # La respuesta ahora también incluye el informe.
    assert properties["informe"]["$ref"] == "#/components/schemas/InformeAnalisis"
