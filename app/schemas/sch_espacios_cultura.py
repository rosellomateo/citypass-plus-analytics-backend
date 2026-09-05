from pydantic import BaseModel


class ReservasPorEspacio(BaseModel):
    espacio: str
    confirmadas: int
    canceladas: int


class InscripcionesPorCategoria(BaseModel):
    categoria: str
    cantidad: int


class InscripcionesPorEvento(BaseModel):
    titulo_evento: str
    inscriptos: int
    capacidad: int
    porcentaje_ocupacion: float | None


class RespuestaAnaliticaEspaciosCultura(BaseModel):
    # Indicadores
    reservas_confirmadas: int
    reservas_canceladas: int
    tasa_cancelacion_porcentaje: float | None
    ocupacion_promedio_porcentaje: float | None

    # Gráficos y tabla
    reservas_por_espacio: list[ReservasPorEspacio]
    inscripciones_por_categoria: list[InscripcionesPorCategoria]
    inscripciones_por_evento: list[InscripcionesPorEvento]