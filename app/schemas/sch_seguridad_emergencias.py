from datetime import datetime

from pydantic import BaseModel


class SeguridadEmergencia(BaseModel):
    estado_actual: str | None
    prioridad: str | None
    cantidadEmergencias: int | None
    tiempoPromRespuestaDespacho: float | None
    tiempoPromRespuestaLugar: float | None
    fecha_snapshot: datetime | None
