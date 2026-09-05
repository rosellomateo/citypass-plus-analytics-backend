from fastapi import APIRouter

from app.schemas.sch_residuos import RespuestaAnaliticaResiduos

router = APIRouter(
    prefix="/analytics/residuos",
    tags=["Residuos"],
)


@router.get("", response_model=RespuestaAnaliticaResiduos)
def obtener_analitica_residuos():

    
    return RespuestaAnaliticaResiduos(
        total_recolectado_toneladas=0.0,
        cantidad_contenedores_criticos=0,
        tasa_recoleccion=0.0,
        tiempo_promedio_vaciado=0.0,
        contenedores_por_estado=[],
        volumen_por_tipo_residuo=[],
        tiempo_vaciado_por_zona=[],
        detalle_contenedores_criticos=[],
    )