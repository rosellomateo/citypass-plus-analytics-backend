"""Movilidad: gold publica afectaciones de estaciones y viajes por causa.
El archivo quedo como viajes_resumen.parquet con la estructura nueva y el
pipeline tambien genera movilidad_resumen.parquet: se usa el mas reciente."""

from datetime import date
from io import BytesIO
from unittest.mock import Mock

import polars as pl
from azure.core.exceptions import ResourceNotFoundError

from app.repositories.parquet_repository import AzureParquetRepository
from app.routers import rout_parte2
from app.services.movilidad_service import (
    BLOB_MOVILIDAD,
    BLOB_VIAJES,
    leer_resumen_movilidad,
    obtener_analitica_viajes,
)
from test.unit.test_routers import make_report


def _resumen(fecha: date, **por_causa) -> pl.DataFrame:
    filas = []
    for causa, (afect, distintas, bloq, prev, rest, viajes) in por_causa.items():
        filas.append(
            {
                "causaTipo": causa,
                "cantidadAfectaciones": afect,
                "estacionesAfectadasDistintas": distintas,
                "cantidadBloqueadas": bloq,
                "estacionesBloqueadasDistintas": bloq,
                "cantidadPreventivas": prev,
                "cantidadRestauradas": rest,
                "cantidadViajesInterrumpidos": viajes,
                "fecha_snapshot": fecha,
            }
        )
    return pl.DataFrame(filas)


def _bytes(df: pl.DataFrame) -> bytes:
    buffer = BytesIO()
    df.write_parquet(buffer)
    return buffer.getvalue()


def _storage(blobs: dict[str, pl.DataFrame]) -> Mock:
    storage = Mock()

    def download(nombre):
        if nombre not in blobs:
            error = ResourceNotFoundError("no existe")
            error.error_code = "BlobNotFound"
            raise error
        return _bytes(blobs[nombre])

    storage.download_blob.side_effect = download
    return storage


HOY = date(2026, 11, 18)
MANANA = date(2026, 11, 19)


def test_lee_viajes_resumen_con_la_estructura_nueva():
    storage = _storage({BLOB_VIAJES: _resumen(HOY, RECLAMO=(21, 20, 6, 0, 12, 0))})

    df = leer_resumen_movilidad(AzureParquetRepository(storage))

    assert df["causaTipo"].to_list() == ["RECLAMO"]


def test_si_movilidad_resumen_es_mas_reciente_usa_ese():
    storage = _storage(
        {
            BLOB_VIAJES: _resumen(HOY, RECLAMO=(21, 20, 6, 0, 12, 0)),
            BLOB_MOVILIDAD: _resumen(MANANA, RECLAMO=(30, 26, 6, 0, 16, 0)),
        }
    )

    df = leer_resumen_movilidad(AzureParquetRepository(storage))

    assert df["cantidadAfectaciones"].to_list() == [30]


def test_viajes_resumen_con_estructura_vieja_se_ignora():
    viejo = pl.DataFrame({"fechaInicio": [HOY], "estacionInicio": ["E1"], "cantidadViajes": [3]})
    storage = _storage(
        {BLOB_VIAJES: viejo, BLOB_MOVILIDAD: _resumen(HOY, NORMAL=(0, 0, 0, 0, 0, 36))}
    )

    df = leer_resumen_movilidad(AzureParquetRepository(storage))

    assert df["causaTipo"].to_list() == ["NORMAL"]


def test_sin_ningun_archivo_devuelve_vacio_sin_romper():
    storage = _storage({})
    reports = Mock()
    reports.read.return_value = make_report("movilidad.json")

    respuesta = obtener_analitica_viajes(AzureParquetRepository(storage), reports)

    assert respuesta.datos == []


def test_endpoint_devuelve_una_fila_por_causa():
    storage = _storage(
        {
            BLOB_VIAJES: _resumen(
                HOY,
                EVENTO_CLIMATICO=(17, 13, 14, 0, 10, 1),
                NORMAL=(0, 0, 0, 0, 0, 36),
            )
        }
    )
    reports = Mock()
    reports.read.return_value = make_report("movilidad.json")

    respuesta = obtener_analitica_viajes(AzureParquetRepository(storage), reports)

    por_causa = {fila.causaTipo: fila for fila in respuesta.datos}
    assert por_causa["EVENTO_CLIMATICO"].cantidadBloqueadas == 14
    assert por_causa["NORMAL"].cantidadViajesInterrumpidos == 36


def test_parte2_movilidad_calcula_los_seis_casos():
    storage = _storage(
        {
            BLOB_VIAJES: _resumen(
                HOY,
                EVENTO_CLIMATICO=(17, 13, 14, 0, 10, 1),
                RECLAMO=(21, 20, 6, 0, 12, 0),
                EVENTO_PUBLICO=(20, 19, 2, 14, 2, 0),
                INCIDENTE_VIAL=(12, 12, 1, 0, 8, 12),
                RESERVA=(12, 12, 0, 0, 5, 0),
                EMERGENCIA=(21, 12, 1, 0, 20, 2),
                NORMAL=(0, 0, 0, 0, 0, 36),
            )
        }
    )

    reporte = rout_parte2.calcular_desde_resumen("mobility", storage)

    valores = {i.id: i.valor for i in reporte.datos}
    assert valores == {"c1": 14, "c2": 20, "c3": 14, "c4": 12, "c5": 2, "c6": 12}
    detalle_c2 = next(i for i in reporte.datos if i.id == "c2").detalle
    assert detalle_c2[0].valor == 21
