from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_espacios_cultura import EspacioCultura
from app.schemas.sch_respuestas import InformeAnalisis, RespuestaEspaciosCultura


def obtener_analitica_espacios(
    repositorio: AzureParquetRepository,
    repositorio_informes: AzureJsonRepository,
) -> RespuestaEspaciosCultura:
    df = repositorio.read("Espacios Publicos y Cultura/actividades_resumen.parquet")
    espacios = [EspacioCultura.model_validate(fila) for fila in df.to_dicts()]

    contenido_json = repositorio_informes.read("espacios.json")
    informe = InformeAnalisis.model_validate(contenido_json)

    return RespuestaEspaciosCultura(datos=espacios, informe=informe)
