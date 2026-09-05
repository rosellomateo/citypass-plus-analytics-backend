from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.sch_espacios_cultura import (
    InscripcionesPorCategoria,
    InscripcionesPorEvento,
    ReservasPorEspacio,
    RespuestaAnaliticaEspaciosCultura,
)
from app.schemas.sch_eventos import RespuestaAnaliticaEventos
from app.schemas.sch_movilidad_urbana import (
    DistribucionDuracionViajes,
    RespuestaAnaliticaMovilidad,
    ViajesPorEstacionOrigen,
    ViajesPorFranjaHoraria,
)
from app.schemas.sch_reclamos import (
    ReclamosPorCategoria,
    ReclamosPorEstado,
    RespuestaAnaliticaReclamos,
    TiempoPromedioCategoria,
)
from app.schemas.sch_residuos import (
    ContenedoresPorEstado,
    DetalleContenedorCritico,
    RespuestaAnaliticaResiduos,
    TiempoPromedioVaciadoPorZona,
    VolumenPorTipoResiduo,
)
from app.schemas.sch_seguridad_emergencias import (
    DespachoPorPrioridad,
    EmergenciasPorEstado,
    EmergenciasPorPrioridad,
    RespuestaAnaliticaSeguridadEmergencias,
)


def test_validates_espacios_cultura_response() -> None:
    response = RespuestaAnaliticaEspaciosCultura(
        reservas_confirmadas=120,
        reservas_canceladas=15,
        tasa_cancelacion_porcentaje=11.11,
        ocupacion_promedio_porcentaje=75.0,
        reservas_por_espacio=[
            ReservasPorEspacio(espacio="Teatro Municipal", confirmadas=80, canceladas=10)
        ],
        inscripciones_por_categoria=[InscripcionesPorCategoria(categoria="Musica", cantidad=65)],
        inscripciones_por_evento=[
            InscripcionesPorEvento(
                titulo_evento="Festival de Jazz",
                inscriptos=90,
                capacidad=100,
                porcentaje_ocupacion=90.0,
            )
        ],
    )

    assert response.ocupacion_promedio_porcentaje is None
    assert response.reservas_por_espacio[0].espacio == "Teatro Municipal"
    assert response.inscripciones_por_evento[0].model_dump() == {
        "titulo_evento": "Festival de Jazz",
        "inscriptos": 90,
        "capacidad": 100,
        "porcentaje_ocupacion": 90.0,
    }


def test_validates_eventos_response() -> None:
    occurred_at = datetime(2026, 9, 5, 14, 30, tzinfo=UTC)

    response = RespuestaAnaliticaEventos(
        id_evento="evt-123",
        tipo_evento="reclamo_creado",
        fecha_hora=occurred_at,
        area="reclamos",
        version="1.0",
        id_correlacion="corr-456",
    )

    assert response.fecha_hora == occurred_at
    assert response.model_dump()["id_correlacion"] == "corr-456"


def test_validates_movilidad_response() -> None:
    response = RespuestaAnaliticaMovilidad(
        total_viajes_iniciados=350,
        duracion_promedio_viaje_minutos=None,
        viajes_por_estacion_origen=[
            ViajesPorEstacionOrigen(estacion="Terminal Norte", cantidad=125)
        ],
        viajes_por_franja_horaria=[ViajesPorFranjaHoraria(franja="08:00-12:00", cantidad=180)],
        distribucion_duracion_viajes=[
            DistribucionDuracionViajes(rango="0-15 minutos", cantidad=95)
        ],
    )

    assert response.duracion_promedio_viaje_minutos is None
    assert response.viajes_por_estacion_origen[0].cantidad == 125
    assert response.distribucion_duracion_viajes[0].rango == "0-15 minutos"


def test_validates_reclamos_response() -> None:
    response = RespuestaAnaliticaReclamos(
        total_reclamos=75,
        tiempo_promedio_resolucion_horas=None,
        reclamos_por_categoria=[ReclamosPorCategoria(categoria="Alumbrado", cantidad=30)],
        reclamos_por_estado=[ReclamosPorEstado(estado="resuelto", cantidad=52)],
        tiempo_resolucion_categoria=[TiempoPromedioCategoria(categoria="Alumbrado", horas=None)],
    )

    assert response.tiempo_promedio_resolucion_horas is None
    assert response.reclamos_por_categoria[0].model_dump() == {
        "categoria": "Alumbrado",
        "cantidad": 30,
    }
    assert response.tiempo_resolucion_categoria[0].horas is None


def test_validates_residuos_response() -> None:
    response = RespuestaAnaliticaResiduos(
        total_recolectado_toneladas=42.5,
        cantidad_contenedores_criticos=3,
        tasa_recoleccion=90.0,
        tiempo_promedio_vaciado=5.75,
        contenedores_por_estado=[ContenedoresPorEstado(estado="critico", cantidad=3)],
        volumen_por_tipo_residuo=[VolumenPorTipoResiduo(tipo_residuo="organico", toneladas=18.25)],
        tiempo_vaciado_por_zona=[TiempoPromedioVaciadoPorZona(zona="centro", horas=None)],
        detalle_contenedores_criticos=[
            DetalleContenedorCritico(
                id_contenedor="cont-10",
                zona="centro",
                tipo_residuo="organico",
                porcentaje_llenado=98.5,
                horas_desbordado=2.0,
            )
        ],
    )

    assert response.tasa_recoleccion is None
    assert response.volumen_por_tipo_residuo[0].toneladas == 18.25
    assert response.detalle_contenedores_criticos[0].id_contenedor == "cont-10"


def test_validates_seguridad_emergencias_response() -> None:
    response = RespuestaAnaliticaSeguridadEmergencias(
        total_emergencias=40,
        emergencias_activas=8,
        emergencias_cerradas=32,
        tiempo_promedio_despacho=7.5,
        emergencias_por_estado=[EmergenciasPorEstado(estado="activa", cantidad=8)],
        emergencias_por_prioridad=[EmergenciasPorPrioridad(prioridad="alta", cantidad=12)],
        despacho_por_prioridad=[DespachoPorPrioridad(prioridad="alta", minutos=None)],
    )

    assert response.emergencias_activas == 8
    assert response.despacho_por_prioridad[0].minutos is None
    assert response.model_dump()["tiempo_promedio_despacho"] == 7.5


@pytest.mark.parametrize(
    "schema",
    [
        RespuestaAnaliticaEspaciosCultura,
        RespuestaAnaliticaEventos,
        RespuestaAnaliticaMovilidad,
        RespuestaAnaliticaReclamos,
        RespuestaAnaliticaResiduos,
        RespuestaAnaliticaSeguridadEmergencias,
    ],
)
def test_rejects_responses_without_required_fields(schema: type[BaseModel]) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate({})


def test_rejects_invalid_numeric_values() -> None:
    with pytest.raises(ValidationError):
        ReclamosPorCategoria(categoria="Alumbrado", cantidad="muchos")
