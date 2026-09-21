from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_espacios_cultura import EspacioCultura


def obtener_analitica_espacios(repositorio: AzureParquetRepository) -> list[EspacioCultura]:

    df = repositorio.read("Espacios Publicos y Cultura/reservas_resumen.parquet")

    espacios = []

    # Se crea una lista de diccionarios y se valida que cada uno cumpla con el schema,
    # de ser asi se lo agrega a la lista de reclamos y se las retorna
    for fila in df.to_dicts():
        espacio = EspacioCultura.model_validate(fila)
        espacios.append(espacio)

    return espacios
