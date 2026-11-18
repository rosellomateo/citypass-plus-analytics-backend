"""Residuos: gold publica intervenciones_resumen y el servicio lo traduce al
contrato Residuo (el de alertas) que sigue esperando el front."""

from datetime import date
from io import BytesIO
from unittest.mock import Mock

import polars as pl

from app.repositories.parquet_repository import AzureParquetRepository
from app.services.residuos_service import (
    SIN_AFECTACION,
    SIN_CAUSA,
    intervenciones_a_residuos,
    obtener_analitica_residuos,
)
from test.unit.test_routers import make_report

GOLD_SCHEMA = {
    "estado_actual": pl.String,
    "causaTipo": pl.String,
    "causaTipoAfectacion": pl.String,
    "barrio": pl.String,
    "origenProgramacion": pl.String,
    "cantidadIntervenciones": pl.Int64,
    "cantidadAfectadas": pl.Int64,
    "cantidadCanceladas": pl.Int64,
    "cantidadCompletadas": pl.Int64,
    "camionesDistintos": pl.Int64,
    "fecha_snapshot": pl.Date,
}


def _fila(**valores):
    base = dict.fromkeys(GOLD_SCHEMA)
    base.update(
        cantidadIntervenciones=0,
        cantidadAfectadas=0,
        cantidadCanceladas=0,
        cantidadCompletadas=0,
        camionesDistintos=0,
        fecha_snapshot=date(2026, 11, 18),
    )
    base.update(valores)
    return base


def test_agrupa_por_los_campos_del_front_y_suma_conteos():
    """origenProgramacion no llega al front: dos filas que solo difieren ahi
    se suman en una."""
    df = pl.DataFrame(
        [
            _fila(
                barrio="Palermo",
                causaTipo="RECLAMO",
                estado_actual="AFECTADA",
                causaTipoAfectacion="EVENTO_CLIMATICO",
                origenProgramacion="EMERGENCIA",
                cantidadIntervenciones=2,
                cantidadCompletadas=1,
            ),
            _fila(
                barrio="Palermo",
                causaTipo="RECLAMO",
                estado_actual="AFECTADA",
                causaTipoAfectacion="EVENTO_CLIMATICO",
                origenProgramacion="ALERTA",
                cantidadIntervenciones=3,
                cantidadCompletadas=0,
            ),
        ],
        schema=GOLD_SCHEMA,
    )

    filas = intervenciones_a_residuos(df)

    assert filas == [
        {
            "zona": "Palermo",
            "tipoAlerta": "RECLAMO",
            "prioridad": "AFECTADA",
            "rangoNivelLlenado": "EVENTO_CLIMATICO",
            "cantidadAlertas": 5,
            "cantidadResueltas": 1,
            "tiempoPromResolucion": None,
            "fecha_snapshot": date(2026, 11, 18),
        }
    ]


def test_causas_nulas_se_muestran_con_etiqueta_legible():
    df = pl.DataFrame(
        [_fila(estado_actual="PROGRAMADA", cantidadIntervenciones=4)], schema=GOLD_SCHEMA
    )

    fila = intervenciones_a_residuos(df)[0]

    assert fila["tipoAlerta"] == SIN_CAUSA
    assert fila["rangoNivelLlenado"] == SIN_AFECTACION
    assert fila["zona"] is None
    assert fila["cantidadAlertas"] == 4


def test_gold_sin_columnas_nuevas_no_rompe():
    """Un gold anterior (sin causaTipoAfectacion/barrio/cantidadCompletadas)
    se traduce igual, con esos campos vacios."""
    viejo = pl.DataFrame(
        {"estado_actual": ["AFECTADA"], "causaTipo": ["RESERVA"], "cantidadIntervenciones": [7]}
    )

    fila = intervenciones_a_residuos(viejo)[0]

    assert fila["prioridad"] == "AFECTADA"
    assert fila["cantidadAlertas"] == 7
    assert fila["cantidadResueltas"] == 0
    assert fila["rangoNivelLlenado"] == SIN_AFECTACION


def test_tabla_vacia_devuelve_lista_vacia():
    assert intervenciones_a_residuos(pl.DataFrame(schema=GOLD_SCHEMA)) == []


def test_servicio_lee_el_parquet_real_y_valida_contra_residuo():
    df = pl.DataFrame(
        [
            _fila(
                barrio="Caballito",
                causaTipo="EVENTO_PUBLICO",
                estado_actual="COMPLETADA",
                cantidadIntervenciones=3,
                cantidadCompletadas=3,
            )
        ],
        schema=GOLD_SCHEMA,
    )
    buffer = BytesIO()
    df.write_parquet(buffer)
    storage = Mock()
    storage.download_blob.return_value = buffer.getvalue()
    reports = Mock()
    reports.read.return_value = make_report("residuos.json")

    respuesta = obtener_analitica_residuos(AzureParquetRepository(storage), reports)

    storage.download_blob.assert_called_once_with(
        "Gestion de Residuos Inteligente/intervenciones_resumen.parquet"
    )
    assert len(respuesta.datos) == 1
    residuo = respuesta.datos[0]
    assert residuo.zona == "Caballito"
    assert residuo.tipoAlerta == "EVENTO_PUBLICO"
    assert residuo.prioridad == "COMPLETADA"
    assert residuo.cantidadAlertas == 3
    assert residuo.cantidadResueltas == 3
    assert residuo.tiempoPromResolucion is None


def test_acepta_causa_programacion_el_nombre_nuevo_de_gold():
    df = pl.DataFrame(
        {
            "estado_actual": ["PROGRAMADA"],
            "causaProgramacion": ["RECLAMO"],
            "cantidadIntervenciones": [2],
        }
    )

    assert intervenciones_a_residuos(df)[0]["tipoAlerta"] == "RECLAMO"
