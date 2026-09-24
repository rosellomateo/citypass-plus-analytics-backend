from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_movilidad_urbana import Movilidad
from app.schemas.sch_respuestas import InformeAnalisis, RespuestaMovilidad


def obtener_analitica_viajes(
    repositorio: AzureParquetRepository,
    repositorio_informes: AzureJsonRepository,
) -> RespuestaMovilidad:
    df = repositorio.read("Movilidad Urbana/viajes_resumen.parquet")

    viajes = []

    # Se crea una lista de diccionarios y se valida que cada uno cumpla con el schema,
    # de ser asi se lo agrega a la lista de reclamos y se las retorna
    for fila in df.to_dicts():
        viaje = Movilidad.model_validate(fila)
        viajes.append(viaje)

    contenido_json = repositorio_informes.read("movilidad.json")
    informe = InformeAnalisis.model_validate(contenido_json)

    return RespuestaMovilidad(datos=viajes, informe=informe)
