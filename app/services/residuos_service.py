import polars as pl

from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_residuos import Residuo
from app.schemas.sch_respuestas import InformeAnalisis, RespuestaResiduos

BLOB_INTERVENCIONES = "Gestion de Residuos Inteligente/intervenciones_resumen.parquet"

# Gold de Residuos dejo de publicar alertas de contenedores (alertas_resumen,
# borrado el 18/11) y ahora publica intervenciones de cuadrillas
# (intervenciones_resumen). El front sigue esperando el contrato viejo de
# alertas (schema Residuo), asi que el servicio traduce una intervencion a
# ese formato para no tener que tocar el front:
#
#   Residuo (contrato del front)  <-  intervenciones_resumen (gold)
#   zona                           <-  barrio
#   tipoAlerta                     <-  causaProgramacion   (por que se programo;
#                                      antes del 18/11 se llamaba causaTipo)
#   prioridad                      <-  estado_actual       (PROGRAMADA/AFECTADA/...)
#   rangoNivelLlenado              <-  causaTipoAfectacion (por que se afecto)
#   cantidadAlertas                <-  cantidadIntervenciones
#   cantidadResueltas              <-  cantidadCompletadas
#   tiempoPromResolucion           <-  (gold no lo publica: null)
#
# Gold tiene una dimension mas (origenProgramacion), asi que se agrupa por las
# cuatro que llegan al front y se suman los conteos: una fila por combinacion.
SIN_CAUSA = "SIN CAUSA EXTERNA"
SIN_AFECTACION = "SIN AFECTACION"

_COLUMNAS_TEXTO = ("barrio", "causaTipo", "estado_actual", "causaTipoAfectacion")
_COLUMNAS_CONTEO = ("cantidadIntervenciones", "cantidadCompletadas")


def normalizar_causa_programacion(df: pl.DataFrame) -> pl.DataFrame:
    """Gold renombro causaTipo -> causaProgramacion el 18/11 (la causa de la
    programacion, para no confundirla con causaTipoAfectacion). Se acepta el
    nombre nuevo y el viejo y se deja siempre como causaTipo."""
    if "causaProgramacion" in df.columns and "causaTipo" not in df.columns:
        return df.rename({"causaProgramacion": "causaTipo"})
    return df


def _completar_columnas(df: pl.DataFrame) -> pl.DataFrame:
    """Agrega como null las columnas que el parquet todavia no tenga (ej. un
    gold anterior a causaTipoAfectacion), para que el servicio no falle."""
    df = normalizar_causa_programacion(df)
    faltantes = [
        pl.lit(None, dtype=pl.String).alias(col) for col in _COLUMNAS_TEXTO if col not in df.columns
    ] + [pl.lit(0, dtype=pl.Int64).alias(col) for col in _COLUMNAS_CONTEO if col not in df.columns]
    if "fecha_snapshot" not in df.columns:
        faltantes.append(pl.lit(None, dtype=pl.Date).alias("fecha_snapshot"))
    return df.with_columns(faltantes) if faltantes else df


def intervenciones_a_residuos(df: pl.DataFrame) -> list[dict]:
    """Traduce las filas de intervenciones_resumen al contrato Residuo."""
    df = _completar_columnas(df)
    if df.is_empty():
        return []

    traducido = (
        df.with_columns(
            pl.col("barrio").cast(pl.String).alias("zona"),
            pl.col("causaTipo").cast(pl.String).fill_null(SIN_CAUSA).alias("tipoAlerta"),
            pl.col("estado_actual").cast(pl.String).alias("prioridad"),
            pl.col("causaTipoAfectacion")
            .cast(pl.String)
            .fill_null(SIN_AFECTACION)
            .alias("rangoNivelLlenado"),
            pl.col("cantidadIntervenciones").cast(pl.Int64).fill_null(0),
            pl.col("cantidadCompletadas").cast(pl.Int64).fill_null(0),
        )
        .group_by(["zona", "tipoAlerta", "prioridad", "rangoNivelLlenado"])
        .agg(
            pl.col("cantidadIntervenciones").sum().alias("cantidadAlertas"),
            pl.col("cantidadCompletadas").sum().alias("cantidadResueltas"),
            pl.col("fecha_snapshot").max().alias("fecha_snapshot"),
        )
        .with_columns(pl.lit(None, dtype=pl.Float64).alias("tiempoPromResolucion"))
        .sort(["zona", "tipoAlerta", "prioridad", "rangoNivelLlenado"], nulls_last=True)
    )
    return traducido.select(
        "zona",
        "tipoAlerta",
        "prioridad",
        "rangoNivelLlenado",
        "cantidadAlertas",
        "cantidadResueltas",
        "tiempoPromResolucion",
        "fecha_snapshot",
    ).to_dicts()


def obtener_analitica_residuos(
    repositorio: AzureParquetRepository,
    repositorio_informes: AzureJsonRepository,
) -> RespuestaResiduos:
    df = repositorio.read(BLOB_INTERVENCIONES)

    # Se traducen las intervenciones al contrato del front y se valida cada
    # fila contra el schema antes de devolverla.
    residuos = [Residuo.model_validate(fila) for fila in intervenciones_a_residuos(df)]
    contenido_json = repositorio_informes.read("residuos.json")
    informe = InformeAnalisis.model_validate(contenido_json)

    return RespuestaResiduos(datos=residuos, informe=informe)
