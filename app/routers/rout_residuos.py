from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.routers.conexion import obtener_repositorio, obtener_repositorio_informes
from app.schemas.sch_respuestas import RespuestaResiduos
from app.services.residuos_service import obtener_analitica_residuos

router = APIRouter(
    prefix="/analytics/residuos",
    tags=["Residuos"],
)


@router.get("", response_model=RespuestaResiduos)
def listar_residuos(
    repositorio: Annotated[AzureParquetRepository, Depends(obtener_repositorio)],
    repositorio_informes: Annotated[AzureJsonRepository, Depends(obtener_repositorio_informes)],
) -> RespuestaResiduos:
    return obtener_analitica_residuos(repositorio, repositorio_informes)
