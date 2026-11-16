from datetime import date

from pydantic import BaseModel


class EspacioCultura(BaseModel):
    """Agregado de actividades de la capa Gold, sin métricas de reservas."""

    estado_actual: str | None
    categoria: str | None
    causaTipo: str | None
    organizadorTipo: str | None
    barrio: str | None
    cantidadActividades: int | None
    cantidadMasivas: int | None
    cantidadAfectadasPorClima: int | None
    totalVecesEventoClimatico: int | None
    totalVecesReclamo: int | None
    totalVecesIncidenteVial: int | None
    totalVecesAccidenteVial: int | None
    fecha_snapshot: date | None
