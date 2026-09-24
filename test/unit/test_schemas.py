from datetime import datetime

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.sch_espacios_cultura import EspacioCultura
from app.schemas.sch_movilidad_urbana import Movilidad
from app.schemas.sch_reclamos import Reclamo
from app.schemas.sch_residuos import Residuo
from app.schemas.sch_seguridad_emergencias import SeguridadEmergencia


def test_validates_espacios_cultura_response() -> None:
    fecha = datetime(2026, 9, 21, 10, 30)

    espacio = EspacioCultura(
        recursoId="REC-001",
        tipoReserva="Presencial",
        categoria="Cultura",
        zona="Centro",
        cupoMaximo=100.0,
        cantidadTotal=80,
        cantidadConfirmadas=70,
        cantidadCanceladas=10,
        inscriptos=75,
        pctOcupacion=75.0,
        fecha_snapshot=fecha,
    )

    assert espacio.recursoId == "REC-001"
    assert espacio.tipoReserva == "Presencial"
    assert espacio.categoria == "Cultura"
    assert espacio.zona == "Centro"
    assert espacio.cupoMaximo == 100.0
    assert espacio.cantidadTotal == 80
    assert espacio.cantidadConfirmadas == 70
    assert espacio.cantidadCanceladas == 10
    assert espacio.inscriptos == 75
    assert espacio.pctOcupacion == 75.0
    assert espacio.fecha_snapshot == fecha


def test_validates_movilidad_response() -> None:
    movilidad = Movilidad(
        fechaInicio=datetime(2026, 9, 21, 10, 30),
        estacionInicio="Estación Central",
        duracionViaje="15 minutos",
        cantidadViajes=10,
        duracionTotalViajes=150.0,
        promDuracion=15.0,
        fecha_snapshot=datetime(2026, 9, 21, 12, 0),
    )

    assert movilidad.fechaInicio == datetime(2026, 9, 21, 10, 30)
    assert movilidad.estacionInicio == "Estación Central"
    assert movilidad.duracionViaje == "15 minutos"
    assert movilidad.cantidadViajes == 10
    assert movilidad.duracionTotalViajes == 150.0
    assert movilidad.promDuracion == 15.0
    assert movilidad.fecha_snapshot == datetime(2026, 9, 21, 12, 0)


def test_validates_reclamos_response() -> None:
    fecha = datetime(2026, 9, 21, 10, 30)

    reclamo = Reclamo(
        barrio="Palermo",
        categoria="Alumbrado",
        prioridad="Alta",
        origenClasificacion="Manual",
        estado_actual="Resuelto",
        row_count=15,
        tiempo_prom_hasta_estado_actual=24.5,
        fecha_snapshot=fecha,
    )

    assert reclamo.barrio == "Palermo"
    assert reclamo.categoria == "Alumbrado"
    assert reclamo.prioridad == "Alta"
    assert reclamo.origenClasificacion == "Manual"
    assert reclamo.estado_actual == "Resuelto"
    assert reclamo.row_count == 15
    assert reclamo.tiempo_prom_hasta_estado_actual == 24.5
    assert reclamo.fecha_snapshot == fecha


def test_validates_residuos_response() -> None:
    fecha = datetime(2026, 9, 21, 10, 30)

    residuo = Residuo(
        zona="Norte",
        tipoAlerta="Contenedor lleno",
        prioridad="Alta",
        rangoNivelLlenado="80-100%",
        cantidadAlertas=20,
        cantidadResueltas=15,
        tiempoPromResolucion=35.5,
        fecha_snapshot=fecha,
    )

    assert residuo.zona == "Norte"
    assert residuo.tipoAlerta == "Contenedor lleno"
    assert residuo.prioridad == "Alta"
    assert residuo.rangoNivelLlenado == "80-100%"
    assert residuo.cantidadAlertas == 20
    assert residuo.cantidadResueltas == 15
    assert residuo.tiempoPromResolucion == 35.5
    assert residuo.fecha_snapshot == fecha


def test_validates_seguridad_emergencias_response() -> None:
    fecha = datetime(2026, 9, 21, 10, 30)

    emergencia = SeguridadEmergencia(
        estado_actual="Resuelta",
        prioridad="Alta",
        cantidadEmergencias=12,
        tiempoPromRespuestaDespacho=4.5,
        tiempoPromRespuestaLugar=9.8,
        fecha_snapshot=fecha,
    )

    assert emergencia.estado_actual == "Resuelta"
    assert emergencia.prioridad == "Alta"
    assert emergencia.cantidadEmergencias == 12
    assert emergencia.tiempoPromRespuestaDespacho == 4.5
    assert emergencia.tiempoPromRespuestaLugar == 9.8
    assert emergencia.fecha_snapshot == fecha


@pytest.mark.parametrize(
    "schema",
    [
        EspacioCultura,
        Movilidad,
        Reclamo,
        Residuo,
        SeguridadEmergencia,
    ],
)
def test_rejects_responses_without_required_fields(schema: type[BaseModel]) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate({})
