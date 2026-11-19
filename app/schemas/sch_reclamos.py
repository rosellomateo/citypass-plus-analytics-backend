from datetime import datetime

from pydantic import BaseModel


class Reclamo(BaseModel):
    barrio: str | None
    categoria: str | None
    prioridad: str | None
    origenClasificacion: str | None
    estado_actual: str | None
    causaTipo: str | None
    # Caso 5 (CU-01): el reclamo es de una emergencia durante un viaje en bici
    # (columna del gold de reclamos). Opcional: un gold viejo no la tiene.
    vinculadoEmergenciaBici: bool | None = None
    row_count: int | None
    tiempo_prom_hasta_estado_actual: float | None
    fecha_snapshot: datetime | None
