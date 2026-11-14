from datetime import date
from typing import Annotated, Literal

import polars as pl
from azure.core.exceptions import AzureError, ResourceNotFoundError
from fastapi import APIRouter, Depends, HTTPException
from polars.exceptions import PolarsError
from pydantic import BaseModel, Field

from app.core.config import AzureStorageSettings
from app.core.security.dependencies import obtener_usuario_actual, require_area
from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_usuario_autenticado import UsuarioAutenticado
from app.storage.azure_blob import AzureBlobStorage

router = APIRouter(prefix="/analytics", tags=["Parte 2"])
Area = Literal["claims", "emergencies", "mobility", "culture", "waste", "dap", "eda"]
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

    if not df["causaTipo"].is_not_null().any():
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


def leer_indicadores(area: Area) -> IndicadoresParteDos:
    try:
        settings = AzureStorageSettings.from_environment()
        with AzureBlobStorage(settings) as storage:
            try:
                result = AzureJsonRepository(storage).read(f"parte2/{area}.json")
            except ResourceNotFoundError as exc:
                if exc.error_code != "BlobNotFound":
                    raise
                return calcular_desde_resumen(area, storage)
        report = IndicadoresParteDos.model_validate(result)
        if len({metric.id for metric in report.datos}) != len(report.datos):
            raise ValueError("Indicadores duplicados")
        if area in {"dap", "eda"} and any(not metric.etiqueta for metric in report.datos):
            raise ValueError("Faltan etiquetas")
        return report
    except (AzureError, PolarsError, ValueError):
        raise HTTPException(503, "No se pudieron consultar los indicadores") from None


@router.get("/{area}/parte2")
def indicadores(
    area: Area,
    usuario: Annotated[UsuarioAutenticado, Depends(obtener_usuario_actual)],
) -> IndicadoresParteDos:
    require_area(area, usuario)
    return leer_indicadores(area)
