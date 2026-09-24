from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_residuos import Residuo
from app.schemas.sch_respuestas import InformeAnalisis, RespuestaResiduos


def obtener_analitica_residuos(
    repositorio: AzureParquetRepository,
    repositorio_informes: AzureJsonRepository,
) -> RespuestaResiduos:
    df = repositorio.read("Gestion de Residuos Inteligente/alertas_resumen.parquet")

    residuos = []

    # Se crea una lista de diccionarios y se valida que cada uno cumpla con el schema,
    # de ser asi se lo agrega a la lista de reclamos y se las retorna
    for fila in df.to_dicts():
        residuo = Residuo.model_validate(fila)
        residuos.append(residuo)
    contenido_json = repositorio_informes.read("residuos.json")
    informe = InformeAnalisis.model_validate(contenido_json)

    return RespuestaResiduos(datos=residuos, informe=informe)
