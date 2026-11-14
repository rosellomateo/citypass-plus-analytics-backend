from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.conexion import obtener_repositorio, obtener_repositorio_informes
from app.core.security.dependencies import require_dashboard
from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_respuestas import RespuestaReclamos
from app.services.reclamos_service import obtener_analitica_reclamos

router = APIRouter(
    prefix="/analytics/reclamos",
    tags=["Reclamos"],
)


@router.get(
    "",
    response_model=RespuestaReclamos,
    dependencies=[Depends(require_dashboard("claims"))],
)

# En el parametro del def se le dice a FastApi "devolveme un objeto de tipo AzureParquetRepository,
# al ejecutar esta función"
def listar_reclamos(
    repositorio: Annotated[
        AzureParquetRepository,
        Depends(obtener_repositorio),
    ],
    repositorio_informes: Annotated[
        AzureJsonRepository,
        Depends(obtener_repositorio_informes),
    ],
):
    return obtener_analitica_reclamos(
        repositorio,
        repositorio_informes,
    )
