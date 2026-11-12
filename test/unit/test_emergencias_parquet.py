from datetime import date
from io import BytesIO
from unittest.mock import Mock

import polars as pl

from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_seguridad_emergencias import SeguridadEmergencia
from app.services.seguridad_emergencias_service import obtener_analitica_emergencias


def test_emergencias_parquet_roundtrip():
    schema = {
        "estado_actual": pl.String, "prioridad": pl.String,
        "categoria": pl.String, "causaTipo": pl.String,
        "afectaCirculacion": pl.Boolean, "cantidadEmergencias": pl.Int64,
        "criticidadAfectada": pl.Int64, "tiempoPromRespuestaDespacho": pl.Float64,
        "tiempoPromRespuestaLugar": pl.Float64, "fecha_snapshot": pl.Date,
    }
    row = {
        "estado_actual": "Resuelta", "prioridad": "Alta",
        "categoria": "Incendio", "causaTipo": "Accidental",
        "afectaCirculacion": False, "cantidadEmergencias": 3_000_000_000,
        "criticidadAfectada": 4_000_000_000, "tiempoPromRespuestaDespacho": 4.5,
        "tiempoPromRespuestaLugar": 9.8, "fecha_snapshot": date(2026, 11, 10),
    }
    rows = [row, dict(row, afectaCirculacion=True), dict.fromkeys(schema)]
    frame = pl.DataFrame(rows, schema=schema)
    buffer = BytesIO()
    frame.write_parquet(buffer)
    storage = Mock()
    storage.download_blob.return_value = buffer.getvalue()
    reports = Mock()
    reports.read.return_value = {
        "actualizado_en": "2026-11-10T00:00:00", "analisis": [],
        "caso_de_uso": "emergencias", "semanas": [],
        "ultima_semana": "2026-W46", "version_esquema": "1",
    }
    result = obtener_analitica_emergencias(AzureParquetRepository(storage), reports)
    assert [item.model_dump() for item in result.datos] == rows
    payload = result.model_dump(mode="json")
    assert payload["datos"][0]["fecha_snapshot"] == "2026-11-10"
    assert payload["datos"][0]["afectaCirculacion"] is False
    assert payload["datos"][1]["afectaCirculacion"] is True
    assert payload["datos"][2] == dict.fromkeys(schema)
    storage.download_blob.assert_called_once_with("Emergencias y Seguridad/emergencias_resumen.parquet")
    reports.read.assert_called_once_with("emergencias.json")


def test_emergencias_openapi_fields():
    properties = SeguridadEmergencia.model_json_schema()["properties"]
    assert len(properties) == 10
    assert properties["fecha_snapshot"]["anyOf"][0] == {"format": "date", "type": "string"}
    assert properties["afectaCirculacion"]["anyOf"][0]["type"] == "boolean"
