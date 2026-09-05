from datetime import datetime

from pydantic import BaseModel


class RespuestaAnaliticaEventos(BaseModel):
    id_evento: str  # ID único del evento generado.
    tipo_evento: str  # Nombre del evento.
    fecha_hora: datetime  # Fecha y hora de ocurrencia en UTC.
    area: str  # Área del sistema a la que pertenece el evento.
    version: str  # Versión del esquema del evento.
    id_correlacion: str  # ID de correlación entre eventos relacionados.
