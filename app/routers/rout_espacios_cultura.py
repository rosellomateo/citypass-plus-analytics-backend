from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.parquet_repository import AzureParquetRepository
from app.routers.conexion import obtener_repositorio
from app.schemas.sch_espacios_cultura import EspacioCultura
from app.services.espacios_cultura_service import obtener_analitica_espacios

router = APIRouter(
    prefix="/analytics/espacios-cultura",
    tags=["Espacios Públicos y Cultura"],
)


@router.get("", response_model=list[EspacioCultura])
# En el parametro del def se le dice a FastApi "devolveme un objeto de tipo AzureParquetRepository,
# al ejecutar esta funión"
def listar_reclamos(repositorio: Annotated[AzureParquetRepository, Depends(obtener_repositorio)]):
    return obtener_analitica_espacios(repositorio)
