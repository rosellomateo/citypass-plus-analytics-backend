from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.parquet_repository import AzureParquetRepository
from app.routers.conexion import obtener_repositorio
from app.schemas.sch_seguridad_emergencias import SeguridadEmergencia
from app.services.seguridad_emergencias_service import obtener_analitica_emergencias

router = APIRouter(
    prefix="/analytics/seguridad-emergencias",
    tags=["Seguridad y Emergencias"],
)


@router.get("", response_model=list[SeguridadEmergencia])
# En el parametro del def se le dice a FastApi "devolveme un objeto de tipo AzureParquetRepository,
# al ejecutar esta función"
def listar_reclamos(repositorio: Annotated[AzureParquetRepository, Depends(obtener_repositorio)]):
    return obtener_analitica_emergencias(repositorio)
