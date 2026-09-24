from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_espacios_cultura import EspacioCultura
from app.schemas.sch_respuestas import InformeAnalisis, RespuestaEspaciosCultura


def obtener_analitica_espacios(
    repositorio: AzureParquetRepository,
    repositorio_informes: AzureJsonRepository,
) -> RespuestaEspaciosCultura:
    df = repositorio.read("Espacios Publicos y Cultura/reservas_resumen.parquet")

    espacios = []

    # Se crea una lista de diccionarios y se valida que cada uno cumpla con el schema,
    # de ser asi se lo agrega a la lista de reclamos y se las retorna
    for fila in df.to_dicts():
        espacio = EspacioCultura.model_validate(fila)
        espacios.append(espacio)

    contenido_json = repositorio_informes.read("espacios.json")
    informe = InformeAnalisis.model_validate(contenido_json)

    return RespuestaEspaciosCultura(datos=espacios, informe=informe)
