from datetime import date
from io import BytesIO
from unittest.mock import Mock

import polars as pl
import pytest
from pydantic import ValidationError

from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_espacios_cultura import EspacioCultura
from app.services.espacios_cultura_service import obtener_analitica_espacios
from test.unit.test_routers import make_report

GOLD_SCHEMA = {
    "estado_actual": pl.String,
    "categoria": pl.String,
    "causaTipo": pl.String,
    "organizadorTipo": pl.String,
    "barrio": pl.String,
    "cantidadActividades": pl.Int64,
    "cantidadMasivas": pl.Int64,
    "cantidadAfectadasPorClima": pl.Int64,
    "totalVecesEventoClimatico": pl.Int64,
    "totalVecesReclamo": pl.Int64,
    "totalVecesIncidenteVial": pl.Int64,
    "totalVecesAccidenteVial": pl.Int64,
    "fecha_snapshot": pl.Date,
}


@pytest.mark.parametrize("empty", [False, True])
def test_actividades_parquet_roundtrip_preserves_aggregates_and_report(empty):
    row = {
        "estado_actual": "SUSPENDIDA",
        "categoria": "CULTURAL",
        "causaTipo": "EVENTO_CLIMATICO",
        "organizadorTipo": "MUNICIPIO",
        "barrio": None,
        "cantidadActividades": 3_000_000_000,
        "cantidadMasivas": 5,
        "cantidadAfectadasPorClima": 12,
        "totalVecesEventoClimatico": 15,
        "totalVecesReclamo": 3,
        "totalVecesIncidenteVial": 2,
        "totalVecesAccidenteVial": 1,
        "fecha_snapshot": date(2026, 11, 15),
    }
    zeros = {name: (0 if dtype == pl.Int64 else None) for name, dtype in GOLD_SCHEMA.items()}
    rows = [] if empty else [row, zeros, dict.fromkeys(GOLD_SCHEMA)]
    frame = pl.DataFrame(rows, schema=GOLD_SCHEMA)
    buffer = BytesIO()
    frame.write_parquet(buffer)
    storage = Mock()
    storage.download_blob.return_value = buffer.getvalue()
    reports = Mock()
    report = make_report("espacios.json")
    reports.read.return_value = report

    result = obtener_analitica_espacios(AzureParquetRepository(storage), reports)

    assert [item.model_dump() for item in result.datos] == rows
    payload = result.model_dump(mode="json")
    assert payload["informe"] == report
    if not empty:
        assert payload["datos"][0]["fecha_snapshot"] == "2026-11-15"
        assert payload["datos"][0]["cantidadActividades"] == 3_000_000_000
        assert payload["datos"][0]["totalVecesIncidenteVial"] == 2
        assert payload["datos"][0]["totalVecesAccidenteVial"] == 1
        assert payload["datos"][1] == zeros
        assert payload["datos"][2] == dict.fromkeys(GOLD_SCHEMA)
    storage.download_blob.assert_called_once_with(
        "Espacios Publicos y Cultura/actividades_resumen.parquet"
    )
    reports.read.assert_called_once_with("espacios.json")


def test_cultura_openapi_exposes_activities_without_reservation_metrics():
    schema = EspacioCultura.model_json_schema()
    assert set(schema["properties"]) == set(GOLD_SCHEMA)
    assert set(schema["required"]) == set(GOLD_SCHEMA)
    assert schema["properties"]["fecha_snapshot"]["anyOf"][0] == {
        "format": "date",
        "type": "string",
    }


def test_legacy_reservation_row_is_not_silently_accepted_as_activities():
    with pytest.raises(ValidationError):
        EspacioCultura.model_validate(
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
                "fecha_snapshot": date(2026, 11, 15),
            }
        )
