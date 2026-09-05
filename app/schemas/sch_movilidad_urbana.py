from pydantic import BaseModel


class ViajesPorEstacionOrigen(BaseModel):
    estacion: str
    cantidad: int


class ViajesPorFranjaHoraria(BaseModel):
    franja: str
    cantidad: int


class DistribucionDuracionViajes(BaseModel):
    rango: str
    cantidad: int


class RespuestaAnaliticaMovilidad(BaseModel):
    # Indicadores
    total_viajes_iniciados: int
    duracion_promedio_viaje_minutos: float | None

    # Gráficos
    viajes_por_estacion_origen: list[ViajesPorEstacionOrigen]
    viajes_por_franja_horaria: list[ViajesPorFranjaHoraria]
    distribucion_duracion_viajes: list[DistribucionDuracionViajes]