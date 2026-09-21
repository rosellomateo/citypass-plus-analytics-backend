from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_reclamos import Reclamo


def obtener_analitica_reclamos(repositorio: AzureParquetRepository) -> list[Reclamo]:

    df = repositorio.read("Reclamos/reclamos_resumen.parquet")

    reclamos = []

    # Se crea una lista de diccionarios y se valida que cada uno cumpla con el schema,
    # de ser asi se lo agrega a la lista de reclamos y se las retorna
    for fila in df.to_dicts():
        reclamo = Reclamo.model_validate(fila)
        reclamos.append(reclamo)

    return reclamos
