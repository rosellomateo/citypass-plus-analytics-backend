from datetime import datetime

from pydantic import BaseModel


class Movilidad(BaseModel):
    """Una fila de gold de Movilidad: afectaciones de estaciones y viajes
    agrupados por la causa que los origino (los 6 casos de uso de la Parte 2).

    causaTipo NORMAL es la fila de viajes finalizados sin incidente: sus
    columnas de afectaciones valen 0 y cantidadViajesInterrumpidos son los
    viajes normales (base de comparacion del caso 5)."""

    causaTipo: str | None
    cantidadAfectaciones: int = 0
    estacionesAfectadasDistintas: int = 0
    cantidadBloqueadas: int = 0
    estacionesBloqueadasDistintas: int = 0
    cantidadPreventivas: int = 0
    cantidadRestauradas: int = 0
    cantidadViajesInterrumpidos: int = 0
    fecha_snapshot: datetime | None = None
