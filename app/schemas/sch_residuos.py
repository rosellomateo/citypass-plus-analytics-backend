from pydantic import BaseModel


class ContenedoresPorEstado(BaseModel):
    estado: str
    cantidad: int


class VolumenPorTipoResiduo(BaseModel):
    tipo_residuo: str
    toneladas: float


class TiempoPromedioVaciadoPorZona(BaseModel):
    zona: str
    horas: float | None


class DetalleContenedorCritico(BaseModel):
    id_contenedor: str
    zona: str
    tipo_residuo: str
    porcentaje_llenado: float
    horas_desbordado: float


class RespuestaAnaliticaResiduos(BaseModel):
    # Indicadores
    total_recolectado_toneladas: float
    cantidad_contenedores_criticos: int
    tasa_recoleccion: float | None
    tiempo_promedio_vaciado: float | None

    # Gráficos y tabla
    contenedores_por_estado: list[ContenedoresPorEstado]
    volumen_por_tipo_residuo: list[VolumenPorTipoResiduo]
    tiempo_vaciado_por_zona: list[TiempoPromedioVaciadoPorZona]
    detalle_contenedores_criticos: list[DetalleContenedorCritico]