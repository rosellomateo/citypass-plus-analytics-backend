from datetime import date

import polars as pl
from azure.core.exceptions import ResourceNotFoundError

from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_movilidad_urbana import Movilidad
from app.schemas.sch_respuestas import InformeAnalisis, RespuestaMovilidad

# Gold de Movilidad publica afectaciones de estaciones y viajes por causa
# (una fila por causaTipo). El archivo quedo como viajes_resumen.parquet con
# esta estructura nueva, y el pipeline lo genera como movilidad_resumen.parquet:
# se leen los dos y se usa el mas reciente que tenga la estructura nueva, para
# no depender de cual de los dos nombres se actualice.
BLOB_VIAJES = "Movilidad Urbana/viajes_resumen.parquet"
BLOB_MOVILIDAD = "Movilidad Urbana/movilidad_resumen.parquet"

COLUMNAS_CONTEO = (
    "cantidadAfectaciones",
    "estacionesAfectadasDistintas",
    "cantidadBloqueadas",
    "estacionesBloqueadasDistintas",
    "cantidadPreventivas",
    "cantidadRestauradas",
    "cantidadViajesInterrumpidos",
)


def _fecha(df: pl.DataFrame) -> date:
    if "fecha_snapshot" not in df.columns or df["fecha_snapshot"].is_null().all():
        return date.min
    return date.fromisoformat(str(df["fecha_snapshot"].max())[:10])


def leer_resumen_movilidad(repositorio: AzureParquetRepository) -> pl.DataFrame:
    """Devuelve el resumen de Movilidad con la estructura nueva (columna
    causaTipo), eligiendo el mas reciente entre viajes_resumen y
    movilidad_resumen. Un archivo que no existe o que tiene la estructura
    vieja de viajes (fecha/estacion/duracion) se ignora."""
    candidatos: list[pl.DataFrame] = []
    for blob in (BLOB_VIAJES, BLOB_MOVILIDAD):
        try:
            df = repositorio.read(blob)
        except ResourceNotFoundError as exc:
            if exc.error_code == "BlobNotFound":
                continue
            raise
        if "causaTipo" in df.columns:
            candidatos.append(df)

    if not candidatos:
        return pl.DataFrame(schema={"causaTipo": pl.String, "fecha_snapshot": pl.Date})
    # max() devuelve el primero ante un empate: viajes_resumen tiene prioridad.
    return max(candidatos, key=_fecha)


def a_filas_movilidad(df: pl.DataFrame) -> list[dict]:
    """Normaliza las filas al DTO Movilidad: conteos nulos o faltantes -> 0."""
    faltantes = [pl.lit(0, dtype=pl.Int64).alias(c) for c in COLUMNAS_CONTEO if c not in df.columns]
    if "fecha_snapshot" not in df.columns:
        faltantes.append(pl.lit(None, dtype=pl.Date).alias("fecha_snapshot"))
    if faltantes:
        df = df.with_columns(faltantes)
    df = df.with_columns([pl.col(c).cast(pl.Int64).fill_null(0) for c in COLUMNAS_CONTEO])
    return df.select("causaTipo", *COLUMNAS_CONTEO, "fecha_snapshot").to_dicts()


def obtener_analitica_viajes(
    repositorio: AzureParquetRepository,
    repositorio_informes: AzureJsonRepository,
) -> RespuestaMovilidad:
    df = leer_resumen_movilidad(repositorio)

    # Se valida cada fila contra el schema antes de devolverla.
    viajes = [Movilidad.model_validate(fila) for fila in a_filas_movilidad(df)]

    contenido_json = repositorio_informes.read("movilidad.json")
    informe = InformeAnalisis.model_validate(contenido_json)

    return RespuestaMovilidad(datos=viajes, informe=informe)
