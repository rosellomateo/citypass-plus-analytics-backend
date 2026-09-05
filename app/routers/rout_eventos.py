from datetime import UTC, datetime

from fastapi import APIRouter

from app.schemas.sch_eventos import RespuestaAnaliticaEventos

router = APIRouter(
    prefix="/analytics/eventos",
    tags=["Eventos"],
)


@router.get("", response_model=RespuestaAnaliticaEventos)
def obtener_evento():

    # Evento temporal para probar el schema.
    return RespuestaAnaliticaEventos(
        id_evento="evento-prueba-001",
        tipo_evento="EmergenciaCreada",
        fecha_hora=datetime(2026, 9, 5, 12, 0, tzinfo=UTC),
        area="EMERGENCIAS",
        version="1.0",
        id_correlacion="correlacion-prueba-001",
    )
