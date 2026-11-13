from datetime import date, datetime
from io import BytesIO
from unittest.mock import Mock

import polars as pl
import pytest

from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_reclamos import Reclamo
from app.services.reclamos_service import obtener_analitica_reclamos


@pytest.mark.parametrize(
    "fecha,dtype",
    [
        (datetime(2026, 11, 10, 15, 30), pl.Datetime),
        (date(2026, 11, 10), pl.Date),
    ],
)
def test_reclamos_parquet_roundtrip(fecha, dtype):
    schema = {
        "barrio": pl.String,
        "categoria": pl.String,
        "prioridad": pl.String,
        "origenClasificacion": pl.String,
        "estado_actual": pl.String,
        "causaTipo": pl.String,
        "row_count": pl.Int64,
        "tiempo_prom_hasta_estado_actual": pl.Float64,
        "fecha_snapshot": dtype,
    }
    row = {
        "barrio": "Palermo",
        "categoria": "Alumbrado",
        "prioridad": "Alta",
        "origenClasificacion": "Manual",
        "estado_actual": "Resuelto",
        "causaTipo": "Falla eléctrica",
        "row_count": 3_000_000_000,
        "tiempo_prom_hasta_estado_actual": 24.5,
        "fecha_snapshot": fecha,
    }
    buffer = BytesIO()
    pl.DataFrame([row, dict.fromkeys(schema)], schema=schema).write_parquet(buffer)
    storage = Mock()
    storage.download_blob.return_value = buffer.getvalue()
    reports = Mock()
    report = {
        "actualizado_en": "2026-11-10T00:00:00",
        "analisis": [],
        "caso_de_uso": "reclamos",
        "semanas": [],
        "ultima_semana": "2026-W46",
        "version_esquema": "1",
    }
    reports.read.return_value = report
    result = obtener_analitica_reclamos(AzureParquetRepository(storage), reports)
    expected = dict(row)
    if not isinstance(fecha, datetime):
        expected["fecha_snapshot"] = datetime.combine(fecha, datetime.min.time())
    assert result.datos[0].model_dump() == expected
    assert result.datos[1].model_dump() == dict.fromkeys(schema)
    payload = result.model_dump(mode="json")
    assert payload["datos"][0]["causaTipo"] == "Falla eléctrica"
    assert payload["informe"] == report
    assert set(Reclamo.model_json_schema()["properties"]) == set(schema)
    storage.download_blob.assert_called_once_with("Reclamos/reclamos_resumen.parquet")
    reports.read.assert_called_once_with("reclamos.json")
