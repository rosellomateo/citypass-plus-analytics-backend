from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.parquet_repository import AzureParquetRepository
from app.routers.conexion import obtener_repositorio
from app.schemas.sch_reclamos import Reclamo
from app.services.reclamos_service import obtener_analitica_reclamos

router = APIRouter(
    prefix="/analytics/reclamos",
    tags=["Reclamos"],
)


@router.get("", response_model=list[Reclamo])
# En el parametro del def se le dice a FastApi "devolveme un objeto de tipo AzureParquetRepository,
# al ejecutar esta funión"
def listar_reclamos(repositorio: Annotated[AzureParquetRepository, Depends(obtener_repositorio)]):
    return obtener_analitica_reclamos(repositorio)
