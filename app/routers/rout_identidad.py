from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.conexion import obtener_repositorio, obtener_repositorio_informes
from app.core.security.dependencies import require_dashboard
from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_respuestas import RespuestaIdentidad
from app.services.identidad_service import obtener_analitica_identidad

router = APIRouter(
    prefix="/analytics/identidad",
    tags=["Identidad"],
)


@router.get(
    "",
    response_model=RespuestaIdentidad,
    dependencies=[Depends(require_dashboard("login"))],
)
def listar_identidad(
    repositorio: Annotated[
        AzureParquetRepository,
        Depends(obtener_repositorio),
    ],
    repositorio_informes: Annotated[
        AzureJsonRepository,
        Depends(obtener_repositorio_informes),
    ],
):
    return obtener_analitica_identidad(
        repositorio,
        repositorio_informes,
    )
