from datetime import date

from pydantic import BaseModel


class SeguridadEmergencia(BaseModel):
    estado_actual: str | None
    prioridad: str | None
    categoria: str | None
    causaTipo: str | None
    afectaCirculacion: bool | None
    cantidadEmergencias: int | None
    criticidadAfectada: int | None
    tiempoPromRespuestaDespacho: float | None
    tiempoPromRespuestaLugar: float | None
    fecha_snapshot: date | None
