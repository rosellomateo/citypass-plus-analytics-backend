from pydantic import BaseModel


class EmergenciasPorEstado(BaseModel):
    estado: str
    cantidad: int


class EmergenciasPorPrioridad(BaseModel):
    prioridad: str
    cantidad: int


class DespachoPorPrioridad(BaseModel):
    prioridad: str
    minutos: float | None


class RespuestaAnaliticaSeguridadEmergencias(BaseModel):
    # Indicadores
    total_emergencias: int
    emergencias_activas: int
    emergencias_cerradas: int
    tiempo_promedio_despacho: float  # En minutos

    # Gráficos
    emergencias_por_estado: list[EmergenciasPorEstado]
    emergencias_por_prioridad: list[EmergenciasPorPrioridad]
    despacho_por_prioridad: list[DespachoPorPrioridad]
