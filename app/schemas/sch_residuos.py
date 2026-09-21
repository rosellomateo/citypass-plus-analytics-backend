from datetime import datetime

from pydantic import BaseModel


class Residuo(BaseModel):
    zona: str | None
    tipoAlerta: str | None
    prioridad: str | None
    rangoNivelLlenado: str | None
    cantidadAlertas: int | None
    cantidadResueltas: int | None
    tiempoPromResolucion: float | None
    fecha_snapshot: datetime | None
