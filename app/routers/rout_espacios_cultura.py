from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.routers.conexion import obtener_repositorio, obtener_repositorio_informes
from app.schemas.sch_respuestas import RespuestaEspaciosCultura
from app.services.espacios_cultura_service import obtener_analitica_espacios

router = APIRouter(
    prefix="/analytics/espacios-cultura",
    tags=["Espacios Públicos y Cultura"],
)


@router.get("", response_model=RespuestaEspaciosCultura)
def listar_espacios(
    repositorio: Annotated[AzureParquetRepository, Depends(obtener_repositorio)],
    repositorio_informes: Annotated[AzureJsonRepository, Depends(obtener_repositorio_informes)],
) -> RespuestaEspaciosCultura:
    return obtener_analitica_espacios(repositorio, repositorio_informes)
