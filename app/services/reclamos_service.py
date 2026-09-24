from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_reclamos import Reclamo
from app.schemas.sch_respuestas import InformeAnalisis, RespuestaReclamos


def obtener_analitica_reclamos(
    repositorio: AzureParquetRepository, repositorio_informes: AzureJsonRepository
) -> list[Reclamo]:

    df = repositorio.read("Reclamos/reclamos_resumen.parquet")

    reclamos = []

    # Se crea una lista de diccionarios y se valida que cada uno cumpla con el schema,
    # de ser asi se lo agrega a la lista de reclamos y se las retorna
    for fila in df.to_dicts():
        reclamo = Reclamo.model_validate(fila)
        reclamos.append(reclamo)

    contenido_json = repositorio_informes.read("reclamos.json")

    informe = InformeAnalisis.model_validate(contenido_json)

    return RespuestaReclamos(
        datos=reclamos,
        informe=informe,
    )
