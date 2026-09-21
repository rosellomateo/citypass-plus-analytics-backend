from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.parquet_repository import AzureParquetRepository
from app.routers.conexion import obtener_repositorio
from app.schemas.sch_movilidad_urbana import Movilidad
from app.services.movilidad_service import obtener_analitica_viajes

router = APIRouter(
    prefix="/analytics/movilidad-urbana",
    tags=["Movilidad Urbana"],
)


@router.get("", response_model=list[Movilidad])
# En el parametro del def se le dice a FastApi "devolveme un objeto de tipo AzureParquetRepository,
# al ejecutar esta funión"
def listar_reclamos(repositorio: Annotated[AzureParquetRepository, Depends(obtener_repositorio)]):
    return obtener_analitica_viajes(repositorio)
