from datetime import datetime

from pydantic import BaseModel


class Reclamo(BaseModel):
    barrio: str | None
    categoria: str | None
    prioridad: str | None
    origenClasificacion: str | None
    estado_actual: str | None
    row_count: int | None
    tiempo_prom_hasta_estado_actual: float | None
    fecha_snapshot: datetime | None
