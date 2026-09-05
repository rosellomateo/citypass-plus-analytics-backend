from fastapi import APIRouter

from app.schemas.sch_reclamos import RespuestaAnaliticaReclamos


router = APIRouter(
    prefix="/analytics/reclamos",
    tags=["Reclamos"],
)


@router.get("", response_model=RespuestaAnaliticaReclamos)
def obtener_analitica_reclamos():
    
    # Datos temporales para probar la estructura de la respuesta.
    return RespuestaAnaliticaReclamos(
        total_reclamos=0,
        tiempo_promedio_resolucion_horas=None,
        reclamos_por_categoria=[],
        reclamos_por_estado=[],
        tiempo_resolucion_categoria=[],
    )