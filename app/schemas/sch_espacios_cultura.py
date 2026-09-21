from datetime import datetime

from pydantic import BaseModel


class EspacioCultura(BaseModel):
    recursoId: str | None
    tipoReserva: str | None
    categoria: str | None
    zona: str | None
    cupoMaximo: float | None
    cantidadTotal: int | None
    cantidadConfirmadas: int | None
    cantidadCanceladas: int | None
    inscriptos: int | None
    pctOcupacion: float | None
    fecha_snapshot: datetime | None
