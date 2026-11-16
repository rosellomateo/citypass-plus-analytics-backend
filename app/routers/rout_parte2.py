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


class IndicadoresParteDos(BaseModel):
    fecha_snapshot: date | None = None
    datos: list[Indicador] = Field(default_factory=list)
    actualizado_en: AwareDatetime | None = None
    version_cultura: int | None = None
    impactos: list[ContextImpact] = Field(default_factory=list)
    eventos_publicos: list[PublicEventImpact] | None = None
    informe: InformeAnalisis | None = None


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

    if not {"causaTipo", count_column}.issubset(df.columns):
        return IndicadoresParteDos()

    snapshot = df["fecha_snapshot"].max() if "fecha_snapshot" in df.columns else None
    if snapshot is not None:
        df = df.filter(pl.col("fecha_snapshot") == snapshot)

    if not df["causaTipo"].is_not_null().any() or df[count_column].null_count():
        return IndicadoresParteDos()

    results = []
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

    snapshot_date = date.fromisoformat(str(snapshot)[:10]) if snapshot is not None else None
    return IndicadoresParteDos(fecha_snapshot=snapshot_date, datos=results)


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
