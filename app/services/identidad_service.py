from azure.core.exceptions import ResourceNotFoundError

from app.repositories.analisis_repository import AzureJsonRepository
from app.repositories.parquet_repository import AzureParquetRepository
from app.schemas.sch_identidad import Identidad
from app.schemas.sch_respuestas import InformeAnalisis, RespuestaIdentidad


def obtener_analitica_identidad(
    repositorio: AzureParquetRepository, repositorio_informes: AzureJsonRepository
) -> RespuestaIdentidad:

    df = repositorio.read("LDAP/autenticacion_resumen.parquet")

    identidad = []

    # Se crea una lista de diccionarios y se valida que cada uno cumpla con el schema,
    # de ser asi se lo agrega a la lista de identidad y se las retorna
    for fila in df.to_dicts():
        evento = Identidad.model_validate(fila)
        identidad.append(evento)

    try:
        contenido_json = repositorio_informes.read("identidad.json")
    except ResourceNotFoundError as exc:
        if getattr(exc, "error_code", None) != "BlobNotFound":
            raise
        informe = None
    else:
        informe = InformeAnalisis.model_validate(contenido_json)

    return RespuestaIdentidad(
        datos=identidad,
        informe=informe,
    )
