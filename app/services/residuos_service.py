from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_residuos import Residuo


def obtener_analitica_residuos(repositorio: AzureParquetRepository) -> list[Residuo]:

    df = repositorio.read("Gestion de Residuos Inteligente/alertas_resumen.parquet")

    residuos = []

    # Se crea una lista de diccionarios y se valida que cada uno cumpla con el schema,
    # de ser asi se lo agrega a la lista de reclamos y se las retorna
    for fila in df.to_dicts():
        residuo = Residuo.model_validate(fila)
        residuos.append(residuo)

    return residuos
