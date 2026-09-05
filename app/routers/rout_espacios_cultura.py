from fastapi import APIRouter

from app.schemas.sch_espacios_cultura import RespuestaAnaliticaEspaciosCultura

router = APIRouter(
    prefix="/analytics/espacios-cultura",
    tags=["Espacios Públicos y Cultura"],
)


@router.get("", response_model=RespuestaAnaliticaEspaciosCultura)
def obtener_analitica_espacios_cultura():

    
    return RespuestaAnaliticaEspaciosCultura(
        reservas_confirmadas=0,
        reservas_canceladas=0,
        tasa_cancelacion_porcentaje=0.0,
        ocupacion_promedio_porcentaje=0.0,
        reservas_por_espacio=[],
        inscripciones_por_categoria=[],
        inscripciones_por_evento=[],
    )