from pydantic import BaseModel


class ReclamosPorCategoria(BaseModel):
    categoria: str
    cantidad: int


class ReclamosPorEstado(BaseModel):
    estado: str
    cantidad: int


class TiempoPromedioCategoria(BaseModel): # Tiempo promedio de resolucion por categoria
    categoria: str
    horas: float | None


class RespuestaAnaliticaReclamos(BaseModel):
    # Indicadores
    total_reclamos: int
    tiempo_promedio_resolucion_horas: float | None

    # Gráficos
    reclamos_por_categoria: list[ReclamosPorCategoria]
    reclamos_por_estado: list[ReclamosPorEstado]
    tiempo_resolucion_categoria: list[TiempoPromedioCategoria]