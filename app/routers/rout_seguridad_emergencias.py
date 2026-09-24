from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.routers.conexion import obtener_repositorio, obtener_repositorio_informes
from app.schemas.sch_respuestas import RespuestaSeguridadEmergencias
from app.services.seguridad_emergencias_service import obtener_analitica_emergencias

router = APIRouter(
    prefix="/analytics/seguridad-emergencias",
    tags=["Seguridad y Emergencias"],
)


@router.get("", response_model=RespuestaSeguridadEmergencias)
def listar_emergencias(
    repositorio: Annotated[AzureParquetRepository, Depends(obtener_repositorio)],
    repositorio_informes: Annotated[AzureJsonRepository, Depends(obtener_repositorio_informes)],
) -> RespuestaSeguridadEmergencias:
    return obtener_analitica_emergencias(repositorio, repositorio_informes)
