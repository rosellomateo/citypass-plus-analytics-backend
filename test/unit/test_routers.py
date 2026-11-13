from datetime import date, datetime

import polars as pl
import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.conexion import obtener_repositorio, obtener_repositorio_informes
from app.core.security.dependencies import obtener_usuario_actual, obtener_validador
from app.main import app
from app.schemas.sch_usuario_autenticado import UsuarioAutenticado


class FakeParquetRepository:
    def __init__(self):
        self.data = {
            "LDAP/autenticacion_resumen.parquet": pl.DataFrame(
                [
                    {
                        "department": None,
                        "username": "usuario-prueba",
                        "event_type": "com.citypass.auth.LoginExitoso",
                        "cantidadEventos": 3_000_000_000,
                        "fecha_snapshot": date(2026, 11, 12),
                    }
                ]
            ),
            "Reclamos/reclamos_resumen.parquet": pl.DataFrame(
                [
                    {
                        "barrio": "Palermo",
                        "categoria": "Alumbrado",
                        "prioridad": "Alta",
                        "origenClasificacion": "Manual",
                        "estado_actual": "Resuelto",
                        "causaTipo": "Falla eléctrica",
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
                        "categoria": "Incendio",
                        "causaTipo": "Accidental",
                        "afectaCirculacion": True,
                        "criticidadAfectada": 3,
                        "cantidadEmergencias": 12,
                        "tiempoPromRespuestaDespacho": 4.5,
                        "tiempoPromRespuestaLugar": 9.8,
                        "fecha_snapshot": date(2026, 9, 21),
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
    "/analytics/identidad": "identidad.json",
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
def client(monkeypatch):
    def usuario_prueba(request: Request):
        return UsuarioAutenticado(
            sub="usuario-prueba",
            groups=["admin"],
            module=MODULOS_POR_RUTA.get(request.url.path, "analitica"),
        )

    app.dependency_overrides[obtener_usuario_actual] = usuario_prueba
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
            "/analytics/identidad",
            [
                {
                    "department": None,
                    "username": "usuario-prueba",
                    "event_type": "com.citypass.auth.LoginExitoso",
                    "cantidadEventos": 3_000_000_000,
                    "fecha_snapshot": "2026-11-12",
                }
            ],
        ),
        (
            "/analytics/reclamos",
            [
                {
                    "barrio": "Palermo",
                    "categoria": "Alumbrado",
                    "prioridad": "Alta",
                    "origenClasificacion": "Manual",
                    "estado_actual": "Resuelto",
                    "causaTipo": "Falla eléctrica",
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
                    "categoria": "Incendio",
                    "causaTipo": "Accidental",
                    "afectaCirculacion": True,
                    "criticidadAfectada": 3,
                    "cantidadEmergencias": 12,
                    "tiempoPromRespuestaDespacho": 4.5,
                    "tiempoPromRespuestaLugar": 9.8,
                    "fecha_snapshot": "2026-09-21",
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
        ("/analytics/identidad", "Identidad"),
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
    if schema == "Identidad":
        assert properties["informe"]["anyOf"] == [
            {"$ref": "#/components/schemas/InformeAnalisis"},
            {"type": "null"},
        ]
    else:
        assert properties["informe"]["$ref"] == "#/components/schemas/InformeAnalisis"


@pytest.mark.parametrize("path", REPORT_FILES)
def test_analytics_rejects_authenticated_user_without_admin(client, path):
    app.dependency_overrides[obtener_usuario_actual] = lambda: UsuarioAutenticado(
        sub="sin-permiso", groups=[], module=MODULOS_POR_RUTA[path]
    )
    response = client.get(path)
    assert response.status_code == 403
    assert response.json() == {"detail": "Se requiere el grupo admin"}


@pytest.mark.parametrize("path", REPORT_FILES)
def test_analytics_requires_bearer_token(client, path):
    del app.dependency_overrides[obtener_usuario_actual]
    # Evita cargar configuracion/JWKS; sin token no se invoca validar.
    app.dependency_overrides[obtener_validador] = lambda: None
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


MODULOS_POR_RUTA = {
    "/analytics/identidad": "identidad",
    "/analytics/espacios-cultura": "espacios",
    "/analytics/movilidad-urbana": "movilidad",
    "/analytics/reclamos": "reclamos",
    "/analytics/residuos": "residuos",
    "/analytics/seguridad-emergencias": "emergencias",
}


@pytest.mark.parametrize("path", MODULOS_POR_RUTA)
@pytest.mark.parametrize(
    "module", ["espacios", "movilidad", "reclamos", "residuos", "emergencias", "analitica"]
)
@pytest.mark.parametrize("admin", [False, True])
def test_module_and_permission_access(client, path, module, admin):
    app.dependency_overrides[obtener_usuario_actual] = lambda: UsuarioAutenticado(
        sub="usuario-prueba",
        groups=["admin"] if admin else ["grupo-prueba"],
        module=module,
    )
    response = client.get(path)
    assert response.status_code == (200 if admin else 403)


def test_identidad_without_report_returns_null(client):
    from unittest.mock import Mock

    from azure.core.exceptions import ResourceNotFoundError

    reports = Mock()
    error = ResourceNotFoundError()
    error.error_code = "BlobNotFound"
    reports.read.side_effect = error
    app.dependency_overrides[obtener_repositorio_informes] = lambda: reports
    response = client.get("/analytics/identidad")
    assert response.status_code == 200
    assert response.json()["informe"] is None
    assert len(response.json()["datos"]) == 1
