from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_movilidad_urbana import Movilidad


def obtener_analitica_viajes(repositorio: AzureParquetRepository) -> list[Movilidad]:

    df = repositorio.read("Movilidad Urbana/viajes_resumen.parquet")

    viajes = []

    # Se crea una lista de diccionarios y se valida que cada uno cumpla con el schema,
    # de ser asi se lo agrega a la lista de reclamos y se las retorna
    for fila in df.to_dicts():
        viaje = Movilidad.model_validate(fila)
        viajes.append(viaje)

    return viajes
