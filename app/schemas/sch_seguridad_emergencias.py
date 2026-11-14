from datetime import date

from pydantic import BaseModel


class SeguridadEmergencia(BaseModel):
    estado_actual: str | None
    prioridad: str | None
    categoria: str | None = None
    causaTipo: str | None = None
    afectaCirculacion: bool | None = None
    cantidadEmergencias: int | None
    criticidadAfectada: int | None = None
    tiempoPromRespuestaDespacho: float | None
    tiempoPromRespuestaLugar: float | None
    fecha_snapshot: date | None
