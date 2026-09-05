from fastapi import APIRouter

from app.schemas.sch_seguridad_emergencias import (
    RespuestaAnaliticaSeguridadEmergencias,
)

router = APIRouter(
    prefix="/analytics/seguridad-emergencias",
    tags=["Seguridad y Emergencias"],
)


@router.get("", response_model=RespuestaAnaliticaSeguridadEmergencias)
def obtener_analitica_seguridad_emergencias():

    return RespuestaAnaliticaSeguridadEmergencias(
        total_emergencias=0,
        emergencias_activas=0,
        emergencias_cerradas=0,
        tiempo_promedio_despacho=0.0,
        emergencias_por_estado=[],
        emergencias_por_prioridad=[],
        despacho_por_prioridad=[],
    )