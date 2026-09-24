from datetime import datetime

from pydantic import BaseModel


class Movilidad(BaseModel):
    fechaInicio: datetime | None
    estacionInicio: str | None
    duracionViaje: str | None
    cantidadViajes: int | None
    duracionTotalViajes: float | None
    promDuracion: float | None
    fecha_snapshot: datetime | None
