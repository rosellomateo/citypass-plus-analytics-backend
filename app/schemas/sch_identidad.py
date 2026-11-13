from datetime import date

from pydantic import BaseModel


class Identidad(BaseModel):
    department: str | None
    username: str | None
    event_type: str | None
    cantidadEventos: int | None
    fecha_snapshot: date | None
