from datetime import date, datetime

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.sch_espacios_cultura import EspacioCultura
from app.schemas.sch_movilidad_urbana import Movilidad
from app.schemas.sch_reclamos import Reclamo
from app.schemas.sch_residuos import Residuo
from app.schemas.sch_seguridad_emergencias import SeguridadEmergencia


def test_validates_espacios_cultura_response() -> None:
    fecha = date(2026, 11, 15)

    espacio = EspacioCultura(
        estado_actual="SUSPENDIDA",
        categoria="CULTURAL",
        causaTipo="EVENTO_CLIMATICO",
        organizadorTipo="MUNICIPIO",
        barrio="Centro",
        cantidadActividades=12,
        cantidadMasivas=5,
        cantidadAfectadasPorClima=12,
        totalVecesEventoClimatico=15,
        totalVecesReclamo=3,
        totalVecesIncidenteVial=2,
        totalVecesAccidenteVial=1,
        fecha_snapshot=fecha,
    )

    assert espacio.estado_actual == "SUSPENDIDA"
    assert espacio.categoria == "CULTURAL"
    assert espacio.causaTipo == "EVENTO_CLIMATICO"
    assert espacio.organizadorTipo == "MUNICIPIO"
    assert espacio.barrio == "Centro"
    assert espacio.cantidadActividades == 12
    assert espacio.cantidadMasivas == 5
    assert espacio.cantidadAfectadasPorClima == 12
    assert espacio.totalVecesEventoClimatico == 15
    assert espacio.totalVecesReclamo == 3
    assert espacio.totalVecesIncidenteVial == 2
    assert espacio.totalVecesAccidenteVial == 1
    assert espacio.fecha_snapshot == fecha


def test_validates_movilidad_response() -> None:
    movilidad = Movilidad(
        causaTipo="RECLAMO",
        cantidadAfectaciones=21,
        estacionesAfectadasDistintas=20,
        cantidadBloqueadas=6,
        estacionesBloqueadasDistintas=6,
        cantidadPreventivas=0,
        cantidadRestauradas=12,
        cantidadViajesInterrumpidos=0,
        fecha_snapshot=datetime(2026, 9, 21, 12, 0),
    )

    assert movilidad.causaTipo == "RECLAMO"
    assert movilidad.cantidadAfectaciones == 21
    assert movilidad.estacionesAfectadasDistintas == 20
    assert movilidad.cantidadBloqueadas == 6
    assert movilidad.cantidadRestauradas == 12
    assert movilidad.fecha_snapshot == datetime(2026, 9, 21, 12, 0)


def test_movilidad_conteos_faltantes_valen_cero() -> None:
    movilidad = Movilidad(causaTipo="NORMAL", cantidadViajesInterrumpidos=36)

    assert movilidad.cantidadAfectaciones == 0
    assert movilidad.cantidadViajesInterrumpidos == 36


def test_validates_reclamos_response() -> None:
    fecha = datetime(2026, 9, 21, 10, 30)

    reclamo = Reclamo(
        barrio="Palermo",
        categoria="Alumbrado",
        prioridad="Alta",
        origenClasificacion="Manual",
        estado_actual="Resuelto",
        causaTipo="Falla eléctrica",
        row_count=15,
        tiempo_prom_hasta_estado_actual=24.5,
        fecha_snapshot=fecha,
    )

    assert reclamo.barrio == "Palermo"
    assert reclamo.categoria == "Alumbrado"
    assert reclamo.prioridad == "Alta"
    assert reclamo.origenClasificacion == "Manual"
    assert reclamo.estado_actual == "Resuelto"
    assert reclamo.causaTipo == "Falla eléctrica"
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
    fecha = date(2026, 9, 21)

    emergencia = SeguridadEmergencia(
        estado_actual="Resuelta",
        prioridad="Alta",
        categoria="Incendio",
        causaTipo="Accidental",
        afectaCirculacion=True,
        criticidadAfectada=3,
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
