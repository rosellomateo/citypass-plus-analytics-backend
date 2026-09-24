from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.sch_reclamos import Reclamo
from app.schemas.sch_espacios_cultura import EspacioCultura
from app.schemas.sch_movilidad_urbana import Movilidad
from app.schemas.sch_residuos import Residuo
from app.schemas.sch_seguridad_emergencias import SeguridadEmergencia


class ResumenAnalisis(BaseModel):
    parrafo_ejecutivo: str
    puntos_destacados: list[str]
    recomendaciones: list[str]
    riesgos: list[str]


class AnalisisSemanal(BaseModel):
    generado_en: datetime
    metadata: dict[str, Any]
    resumen: ResumenAnalisis
    semana: str


class InformeAnalisis(BaseModel):
    actualizado_en: datetime
    analisis: list[AnalisisSemanal]
    caso_de_uso: str
    semanas: list[str]
    ultima_semana: str
    version_esquema: str


class RespuestaReclamos(BaseModel):
    datos: list[Reclamo]
    informe: InformeAnalisis


class RespuestaEspaciosCultura(BaseModel):
    datos: list[EspacioCultura]
    informe: InformeAnalisis


class RespuestaMovilidad(BaseModel):
    datos: list[Movilidad]
    informe: InformeAnalisis


class RespuestaResiduos(BaseModel):
    datos: list[Residuo]
    informe: InformeAnalisis


class RespuestaSeguridadEmergencias(BaseModel):
    datos: list[SeguridadEmergencia]
    informe: InformeAnalisis
