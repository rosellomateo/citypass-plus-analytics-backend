from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.routers.conexion import obtener_repositorio, obtener_repositorio_informes
from app.schemas.sch_respuestas import RespuestaMovilidad
from app.services.movilidad_service import obtener_analitica_viajes

router = APIRouter(
    prefix="/analytics/movilidad-urbana",
    tags=["Movilidad Urbana"],
)


@router.get("", response_model=RespuestaMovilidad)
def listar_viajes(
    repositorio: Annotated[AzureParquetRepository, Depends(obtener_repositorio)],
    repositorio_informes: Annotated[AzureJsonRepository, Depends(obtener_repositorio_informes)],
) -> RespuestaMovilidad:
    return obtener_analitica_viajes(repositorio, repositorio_informes)
