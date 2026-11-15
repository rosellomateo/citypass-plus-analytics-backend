from datetime import date
from io import BytesIO
from unittest.mock import Mock

import polars as pl
import pytest
from pydantic import ValidationError

from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_identidad import Identidad
from app.services.identidad_service import obtener_analitica_identidad
from test.unit.test_routers import make_report


@pytest.mark.parametrize("empty", [False, True])
def test_identidad_parquet_roundtrip(empty):
    schema = {
        "department": pl.String,
        "username": pl.String,
        "event_type": pl.String,
        "cantidadEventos": pl.Int64,
        "fecha_snapshot": pl.Date,
    }
    row = {
        "department": None,
        "username": "usuario-prueba",
        "event_type": "com.citypass.auth.LoginExitoso",
        "cantidadEventos": 3_000_000_000,
        "fecha_snapshot": date(2026, 11, 12),
    }
    rows = [] if empty else [row, dict.fromkeys(schema)]
    buffer = BytesIO()
    pl.DataFrame(rows, schema=schema).write_parquet(buffer)
    storage = Mock()
    storage.download_blob.return_value = buffer.getvalue()
    reports = Mock()
    reports.read.return_value = make_report("identidad.json")
    result = obtener_analitica_identidad(AzureParquetRepository(storage), reports)
    assert [item.model_dump() for item in result.datos] == rows
    assert result.model_dump(mode="json")["informe"] == make_report("identidad.json")
    assert set(Identidad.model_fields) == set(schema)
    storage.download_blob.assert_called_once_with("LDAP/autenticacion_resumen.parquet")
    reports.read.assert_called_once_with("identidad.json")


def test_identidad_rejects_missing_column():
    with pytest.raises(ValidationError):
        Identidad.model_validate(
            {
                "department": "reclamos",
                "username": "usuario",
                "event_type": "login",
                "fecha_snapshot": "2026-11-12",
            }
        )
