from fastapi import APIRouter

from app.schemas.sch_movilidad_urbana import RespuestaAnaliticaMovilidad

router = APIRouter(
    prefix="/analytics/movilidad-urbana",
    tags=["Movilidad Urbana"],
)


@router.get("", response_model=RespuestaAnaliticaMovilidad)
def obtener_analitica_movilidad():

    return RespuestaAnaliticaMovilidad(
        total_viajes_iniciados=0,
        duracion_promedio_viaje_minutos=0.0,
        viajes_por_estacion_origen=[],
        viajes_por_franja_horaria=[],
        distribucion_duracion_viajes=[],
    )
