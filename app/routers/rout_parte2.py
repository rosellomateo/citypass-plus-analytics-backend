import json
import os
from datetime import date
from typing import Annotated, Literal
from urllib.parse import urlparse
from urllib.request import urlopen

import polars as pl
from azure.core.exceptions import AzureError, ResourceNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Response
from polars.exceptions import PolarsError
from pydantic import AwareDatetime, BaseModel, Field

from app.core.config import AzureStorageSettings
from app.core.security.dependencies import requerir_admin
from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_respuestas import InformeAnalisis
from app.services.parte2_events import (
    ContextImpact,
    Part2Events,
    PublicEventImpact,
    context_impacts,
    culture_counts,
    public_event_impacts,
)
from app.services.residuos_service import normalizar_causa_programacion
from app.storage.azure_blob import AzureBlobStorage

router = APIRouter(prefix="/analytics", tags=["Parte 2"])
Area = Literal["claims", "emergencies", "mobility", "culture", "waste", "eda"]
AVAILABLE_CAUSES = {
    "claims": (
        "Reclamos/reclamos_resumen.parquet",
        "row_count",
        {
            "c1": "EVENTO_CLIMATICO",
            "c3": "EVENTO_PUBLICO",
            "c6": "RESERVA",
        },
    ),
    "emergencies": (
        "Emergencias y Seguridad/emergencias_resumen.parquet",
        "cantidadEmergencias",
        {
            "c1": "EVENTO_CLIMATICO",
            "c2": "RECLAMO",
            "c6": "RESERVA",
        },
    ),
    # Movilidad, Residuos y Espacios calculan desde gold el caso 1 (evento
    # climático, ver _caso1()) y el caso 5 (CU-01, emergencia durante un viaje
    # en bici, ver _caso5()).
    "mobility": ("Movilidad Urbana/movilidad_resumen.parquet", "cantidadAfectaciones", {}),
    "waste": (
        "Gestion de Residuos Inteligente/intervenciones_resumen.parquet",
        "cantidadIntervenciones",
        {},
    ),
    "culture": (
        "Espacios Publicos y Cultura/actividades_resumen.parquet",
        "cantidadActividades",
        {},
    ),
}

# Nombres de causa tal como los colorea el front (CausePie.tsx).
ETIQUETAS_CAUSA = {
    "EVENTO_PUBLICO": "Evento público",
    "EVENTO_CLIMATICO": "Clima",
    "RECLAMO": "Reclamo",
    "INCIDENTE_VIAL": "Incidente vial",
    "ACCIDENTE_VIAL": "Accidente vial",
    "EMERGENCIA": "Emergencia",
    "RESERVA": "Reserva",
    "NORMAL": "Operación normal",
}


class DetalleIndicador(BaseModel):
    etiqueta: str
    valor: Annotated[float, Field(allow_inf_nan=False)]


class Indicador(BaseModel):
    id: Annotated[str, Field(min_length=1)]
    etiqueta: str | None = None
    valor: Annotated[float, Field(allow_inf_nan=False)]
    unidad: str | None = None
    detalle: list[DetalleIndicador] = Field(default_factory=list)


class PuntoGrafico(BaseModel):
    etiqueta: str
    valor: Annotated[float, Field(allow_inf_nan=False)]


class GraficoGold(BaseModel):
    """Gráfico armado desde una tabla gold (GoldReportChart en el front)."""

    id: str
    titulo: str
    fecha_snapshot: date
    puntos: list[PuntoGrafico] = Field(default_factory=list)


class IndicadoresParteDos(BaseModel):
    fecha_snapshot: date | None = None
    datos: list[Indicador] = Field(default_factory=list)
    actualizado_en: AwareDatetime | None = None
    version_cultura: int | None = None
    impactos: list[ContextImpact] = Field(default_factory=list)
    eventos_publicos: list[PublicEventImpact] | None = None
    informe: InformeAnalisis | None = None
    resumen_gold: list[GraficoGold] = Field(default_factory=list)


def _suma(df: pl.DataFrame, columna: str, causa: str) -> float:
    return df.filter(pl.col("causaTipo") == causa)[columna].sum()


def _sumar(df: pl.DataFrame, columna: str) -> float:
    return df[columna].sum() if columna in df.columns else 0


def _caso2(area: Area, df: pl.DataFrame) -> list[Indicador]:
    """Reclamos que Gold vinculó con al menos otro módulo, sin contar sus eventos."""
    if area != "claims" or not {"afectaOtrosModulos", "row_count"}.issubset(df.columns):
        return []
    if (
        df.schema["afectaOtrosModulos"] != pl.Boolean
        or df["afectaOtrosModulos"].null_count()
        or not df.schema["row_count"].is_numeric()
        or df["row_count"].null_count()
    ):
        return []
    afectados = df.filter(pl.col("afectaOtrosModulos"))
    return [Indicador(id="c2", valor=afectados["row_count"].sum())]


def _caso1(area: Area, df: pl.DataFrame) -> list[Indicador]:
    """Caso 1 (evento climático) en los módulos que no lo leen de AVAILABLE_CAUSES.
    Cada módulo usa la columna gold que describe su propio impacto."""
    if area == "mobility":
        columnas = {"cantidadBloqueadas", "estacionesBloqueadasDistintas"}
        if not columnas.issubset(df.columns):
            return []
        clima = df.filter(pl.col("causaTipo") == "EVENTO_CLIMATICO")
        return [
            Indicador(
                id="c1",
                valor=_sumar(clima, "estacionesBloqueadasDistintas"),
                detalle=[
                    DetalleIndicador(
                        etiqueta="Bloqueos registrados", valor=_sumar(clima, "cantidadBloqueadas")
                    )
                ],
            )
        ]

    if area == "waste":
        # La causa de la afectación va en su propia columna: causaTipo es la
        # causa de la programación de la intervención.
        if not {"causaTipoAfectacion", "cantidadAfectadas"}.issubset(df.columns):
            return []
        clima = df.filter(pl.col("causaTipoAfectacion") == "EVENTO_CLIMATICO")
        return [Indicador(id="c1", valor=_sumar(clima, "cantidadAfectadas"))]

    if area == "culture":
        if not {"categoria", "estado_actual", "cantidadActividades"}.issubset(df.columns):
            return []
        afectadas = df.filter(
            (pl.col("causaTipo") == "EVENTO_CLIMATICO")
            & pl.col("estado_actual").is_in(["CANCELADA", "SUSPENDIDA"])
        )
        culturales = afectadas.filter(pl.col("categoria").str.to_uppercase() == "CULTURAL")
        return [
            Indicador(
                id="c1",
                valor=_sumar(culturales, "cantidadActividades"),
                detalle=[
                    DetalleIndicador(
                        etiqueta="Todas las categorías",
                        valor=_sumar(afectadas, "cantidadActividades"),
                    )
                ],
            )
        ]

    return []


def _caso5(area: Area, df: pl.DataFrame, count_column: str) -> list[Indicador]:
    """Caso 5 (CU-01): cada módulo cuenta solo con sus propios eventos, por
    el causaTipo que publica (no se cruzan módulos). Los nombres de las
    tarjetas los pone el front (PART2_METRICS); acá van id, valor y detalle."""
    if area == "emergencies":
        bici = df.filter(pl.col("causaTipo") == "MOVILIDAD_BICICLETA")
        resultado = [Indicador(id="c5", valor=bici[count_column].sum())]
        if "tiempoPromResolucion" in df.columns:
            # El gold repite el mismo promedio en todas las filas de la causa.
            tiempos = bici["tiempoPromResolucion"].drop_nulls().drop_nans()
            if len(tiempos) > 0:
                resultado.append(
                    Indicador(id="c5b", valor=round(float(tiempos[0]), 1), unidad="min")
                )
        return resultado

    if area == "claims":
        por_emergencia = _suma(df, count_column, "EMERGENCIA")
        otras = df[count_column].sum() - por_emergencia
        return [
            Indicador(
                id="c5",
                valor=por_emergencia,
                detalle=[DetalleIndicador(etiqueta="Otras causas", valor=otras)],
            )
        ]

    if area == "mobility":
        if "cantidadViajesInterrumpidos" not in df.columns:
            return []
        viajes = "cantidadViajesInterrumpidos"
        return [
            Indicador(
                id="c5",
                valor=_suma(df, viajes, "EMERGENCIA"),
                detalle=[
                    DetalleIndicador(
                        etiqueta="Viajes finalizados normalmente",
                        valor=_suma(df, viajes, "NORMAL"),
                    )
                ],
            )
        ]

    if area == "waste":
        # Gold separa por origenProgramacion: EMERGENCIA (emergenciaId no nulo)
        # vs. ALERTA. Sin esa columna (gold viejo) se usa la causa.
        if "origenProgramacion" in df.columns:
            emergencia = df.filter(pl.col("origenProgramacion") == "EMERGENCIA")
            return [Indicador(id="c5", valor=emergencia[count_column].sum())]
        return [Indicador(id="c5", valor=_suma(df, count_column, "EMERGENCIA"))]

    if area == "culture":
        return [Indicador(id="c5", valor=_suma(df, count_column, "ACCIDENTE_VIAL"))]

    return []


def _puntos_por_causa(df: pl.DataFrame, columna: str, sin_causa: str | None) -> list[PuntoGrafico]:
    """Suma `columna` por causaTipo. Las filas sin causa van con la etiqueta
    `sin_causa`, o se omiten si es None. Los valores vacíos o basura ("")
    se omiten."""
    totales: dict[str, float] = {}
    for causa, valor in df.group_by("causaTipo").agg(pl.col(columna).sum()).iter_rows():
        if causa is None:
            if sin_causa is None:
                continue
            etiqueta = sin_causa
        elif not str(causa).strip():
            continue
        else:
            etiqueta = ETIQUETAS_CAUSA.get(causa, str(causa).replace("_", " ").capitalize())
        totales[etiqueta] = totales.get(etiqueta, 0) + (valor or 0)
    return [
        PuntoGrafico(etiqueta=etiqueta, valor=valor)
        for etiqueta, valor in sorted(totales.items(), key=lambda par: (-par[1], par[0]))
    ]


def _graficos_gold(
    area: Area, df: pl.DataFrame, count_column: str, snapshot: date | None
) -> list[GraficoGold]:
    """Gráficos por causa que el front busca por id en resumen_gold."""
    if snapshot is None:
        return []
    if area == "waste":
        return [
            GraficoGold(
                id="waste-cause",
                titulo="Intervenciones por causa publicada",
                fecha_snapshot=snapshot,
                puntos=_puntos_por_causa(df, count_column, "Operación normal"),
            )
        ]
    if area == "culture":
        return [
            GraficoGold(
                id="culture-cause",
                titulo="Actividades por causa publicada",
                fecha_snapshot=snapshot,
                puntos=_puntos_por_causa(df, count_column, None),
            )
        ]
    if area == "mobility":
        graficos = [
            GraficoGold(
                id="mobility-stations",
                titulo="Estaciones afectadas por causa",
                fecha_snapshot=snapshot,
                puntos=[
                    punto
                    for punto in _puntos_por_causa(df, count_column, None)
                    if punto.etiqueta != ETIQUETAS_CAUSA["NORMAL"]
                ],
            )
        ]
        if "cantidadViajesInterrumpidos" in df.columns:
            graficos.append(
                GraficoGold(
                    id="mobility-interruptions",
                    titulo="Viajes por causa de interrupción",
                    fecha_snapshot=snapshot,
                    puntos=_puntos_por_causa(df, "cantidadViajesInterrumpidos", None),
                )
            )
        return graficos
    return []


def calcular_desde_resumen(area: Area, storage: AzureBlobStorage) -> IndicadoresParteDos:
    if area not in AVAILABLE_CAUSES:
        return IndicadoresParteDos()

    path, count_column, causes = AVAILABLE_CAUSES[area]
    try:
        df = AzureParquetRepository(storage).read(path)
    except ResourceNotFoundError as exc:
        if exc.error_code == "BlobNotFound":
            return IndicadoresParteDos()
        raise

    if area == "waste":
        # Gold de Residuos renombro causaTipo -> causaProgramacion (18/11).
        df = normalizar_causa_programacion(df)

    if count_column not in df.columns:
        return IndicadoresParteDos()

    snapshot = df["fecha_snapshot"].max() if "fecha_snapshot" in df.columns else None
    if snapshot is not None:
        df = df.filter(pl.col("fecha_snapshot") == snapshot)

    snapshot_date = date.fromisoformat(str(snapshot)[:10]) if snapshot is not None else None
    # El reclamo ciudadano puede no tener causa externa y aun así afectar a
    # otros módulos. c2 usa la bandera de Gold, independientemente de causaTipo.
    results = _caso2(area, df)
    if (
        "causaTipo" not in df.columns
        or not df["causaTipo"].is_not_null().any()
        or df[count_column].null_count()
    ):
        return IndicadoresParteDos(
            fecha_snapshot=snapshot_date if results else None,
            datos=results,
        )

    for metric_id, cause in causes.items():
        matching = df.filter(pl.col("causaTipo") == cause)
        if area == "emergencies" and metric_id == "c1":
            if "criticidadAfectada" in df.columns and matching["criticidadAfectada"].len() > 0:
                known = matching["criticidadAfectada"].drop_nulls()
                if len(known) == len(matching):
                    results.append(
                        Indicador(
                            id=metric_id,
                            valor=known.sum(),
                            detalle=[
                                DetalleIndicador(
                                    etiqueta="Emergencias vinculadas al clima",
                                    valor=matching[count_column].sum(),
                                )
                            ],
                        )
                    )
        else:
            results.append(Indicador(id=metric_id, valor=matching[count_column].sum()))

    results.extend(_caso1(area, df))
    results.extend(_caso5(area, df, count_column))

    return IndicadoresParteDos(
        fecha_snapshot=snapshot_date,
        datos=results,
        # El front solo muestra las tarjetas de Espacios con version_cultura == 2.
        version_cultura=2 if area == "culture" else None,
        resumen_gold=_graficos_gold(area, df, count_column, snapshot_date),
    )


def read_report(storage: AzureBlobStorage, area: Area) -> IndicadoresParteDos:
    try:
        result = AzureJsonRepository(storage).read(f"parte2/{area}.json")
    except ResourceNotFoundError as exc:
        if exc.error_code != "BlobNotFound":
            raise
        return calcular_desde_resumen(area, storage)
    return IndicadoresParteDos.model_validate(result)


def read_event_feed(storage: AzureBlobStorage) -> Part2Events | None:
    endpoint = os.getenv("PART2_EVENTS_URL", "").strip()
    if endpoint:
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("El endpoint de eventos debe ser HTTPS")
        with urlopen(endpoint, timeout=5) as response:
            payload = response.read(10_000_001)
            if len(payload) > 10_000_000:
                raise ValueError("El corte de eventos supera el tamaño permitido")
        return Part2Events.model_validate(json.loads(payload))

    path = os.getenv("PART2_EVENTS_BLOB", "").strip() or "parte2/eventos.json"
    try:
        return Part2Events.model_validate(AzureJsonRepository(storage).read(path))
    except ResourceNotFoundError as exc:
        if exc.error_code == "BlobNotFound":
            return None
        raise


def report_from_events(
    storage: AzureBlobStorage, area: Area, report: IndicadoresParteDos
) -> IndicadoresParteDos:
    if area == "culture" and report.version_cultura != 2:
        report = IndicadoresParteDos()
    if area not in {"culture", "emergencies", "eda"}:
        return report
    feed = read_event_feed(storage)
    if feed is None:
        return report

    if "emergencies" in feed.cobertura:
        report.eventos_publicos = public_event_impacts(feed)

    if area == "eda":
        return report

    if area == "emergencies":
        if "emergencies" in feed.cobertura:
            report.impactos = context_impacts(feed)
        return report

    if "culture" not in feed.cobertura:
        return report

    if report.version_cultura == 2 and report.actualizado_en is not None:
        if report.actualizado_en >= feed.actualizado_en:
            return report
    return IndicadoresParteDos(
        actualizado_en=feed.actualizado_en,
        version_cultura=2,
        eventos_publicos=report.eventos_publicos,
        resumen_gold=report.resumen_gold,
        datos=[
            Indicador(
                id=metric_id,
                valor=count,
                detalle=[DetalleIndicador(etiqueta=label, valor=value) for label, value in detail],
            )
            for metric_id, (count, detail) in culture_counts(feed).items()
        ],
    )


def leer_indicadores(area: Area) -> IndicadoresParteDos:
    try:
        settings = AzureStorageSettings.from_environment()
        with AzureBlobStorage(settings) as storage:
            report = report_from_events(storage, area, read_report(storage, area))
        if len({metric.id for metric in report.datos}) != len(report.datos):
            raise ValueError("Indicadores duplicados")
        if area == "eda" and any(not metric.etiqueta for metric in report.datos):
            raise ValueError("Faltan etiquetas")
        return report
    except (AzureError, OSError, PolarsError, ValueError):
        raise HTTPException(
            503,
            "No se pudieron consultar los indicadores",
            headers={"Cache-Control": "private, no-store"},
        ) from None


@router.get(
    "/{area}/parte2",
    response_model=IndicadoresParteDos,
    dependencies=[Depends(requerir_admin)],
)
def indicadores(
    area: Area,
    response: Response,
) -> IndicadoresParteDos:
    response.headers["Cache-Control"] = "private, no-store"
    return leer_indicadores(area)
