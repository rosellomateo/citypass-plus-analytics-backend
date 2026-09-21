from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_seguridad_emergencias import SeguridadEmergencia


def obtener_analitica_emergencias(repositorio: AzureParquetRepository) -> list[SeguridadEmergencia]:

    df = repositorio.read("Emergencias y Seguridad/emergencias_resumen.parquet")

    emergencias = []

    # Se crea una lista de diccionarios y se valida que cada uno cumpla con el schema,
    # de ser asi se lo agrega a la lista de reclamos y se las retorna
    for fila in df.to_dicts():
        emergencia = SeguridadEmergencia.model_validate(fila)
        emergencias.append(emergencia)

    return emergencias
