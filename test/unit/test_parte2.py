from datetime import date

import polars as pl
import pytest

from app.routers import rout_parte2


def test_emergencies_part2_uses_latest_snapshot_and_counts_adjusted_priority(monkeypatch):
    rows = pl.DataFrame(
        {
            "fecha_snapshot": [date(2026, 11, 11), date(2026, 11, 12), date(2026, 11, 12)],
            "causaTipo": ["EVENTO_CLIMATICO", "EVENTO_CLIMATICO", "RECLAMO"],
            "cantidadEmergencias": [100, 8, 3],
            "criticidadAfectada": [90, 2, None],
        }
    )
    monkeypatch.setattr(rout_parte2.AzureParquetRepository, "read", lambda self, path: rows)

    report = rout_parte2.calcular_desde_resumen("emergencies", None)

    assert report.fecha_snapshot == date(2026, 11, 12)
    values = {item.id: item.valor for item in report.datos}
    assert values == {"c1": 2, "c2": 3, "c6": 0, "c5": 0}
    assert report.datos[0].detalle[0].valor == 8


def test_old_snapshot_without_cause_stays_pending(monkeypatch):
    monkeypatch.setattr(
        rout_parte2.AzureParquetRepository,
        "read",
        lambda self, path: pl.DataFrame({"row_count": [10]}),
    )
    assert rout_parte2.calcular_desde_resumen("claims", None).datos == []


def test_unknown_counts_are_not_reported_as_zero(monkeypatch):
    monkeypatch.setattr(
        rout_parte2.AzureParquetRepository,
        "read",
        lambda self, path: pl.DataFrame({"causaTipo": ["EVENTO_CLIMATICO"], "row_count": [None]}),
    )
    assert rout_parte2.calcular_desde_resumen("claims", None).datos == []


# --- Caso 5 (CU-01, emergencia durante un viaje en bici) -------------------
# Las tablas imitan la forma de las gold reales (snapshot 17/11/2026).

SNAP = date(2026, 11, 17)


def leer(monkeypatch, rows):
    monkeypatch.setattr(rout_parte2.AzureParquetRepository, "read", lambda self, path: rows)


def by_id(report):
    return {item.id: item for item in report.datos}


def test_reclamos_caso2_suma_reclamos_del_ultimo_snapshot_y_conserva_casos_existentes(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [date(2026, 11, 16), SNAP, SNAP, SNAP],
                "causaTipo": ["EMERGENCIA", "EMERGENCIA", None, "RESERVA"],
                "afectaOtrosModulos": [True, True, True, False],
                "row_count": [100, 2, 3, 10],
            }
        ),
    )
    report = rout_parte2.calcular_desde_resumen("claims", None)
    datos = by_id(report)
    assert report.fecha_snapshot == SNAP
    assert datos["c2"].valor == 5  # suma entidades, no las dos filas agregadas
    assert datos["c5"].valor == 2
    assert datos["c6"].valor == 10


@pytest.mark.parametrize("con_columna_causa", [True, False])
def test_reclamos_caso2_no_depende_de_la_causa_del_reclamo(monkeypatch, con_columna_causa):
    rows = pl.DataFrame(
        {
            "fecha_snapshot": [SNAP, SNAP],
            "afectaOtrosModulos": [True, False],
            "row_count": [4, 9],
        }
    )
    if con_columna_causa:
        rows = rows.with_columns(pl.lit(None, dtype=pl.String).alias("causaTipo"))
    leer(monkeypatch, rows)
    report = rout_parte2.calcular_desde_resumen("claims", None)
    assert report.fecha_snapshot == SNAP
    assert {item.id: item.valor for item in report.datos} == {"c2": 4}


def test_reclamos_caso2_publica_cero_si_no_hay_reclamos_afectados(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame({"afectaOtrosModulos": [False, False], "row_count": [2, 5]}),
    )
    assert by_id(rout_parte2.calcular_desde_resumen("claims", None))["c2"].valor == 0


@pytest.mark.parametrize(
    "columns",
    [
        {"row_count": [2, 5]},
        {"afectaOtrosModulos": [True, None], "row_count": [2, 5]},
        {"afectaOtrosModulos": ["true", "false"], "row_count": [2, 5]},
        {"afectaOtrosModulos": [True, False], "row_count": [None, 5]},
        {"afectaOtrosModulos": [True, False], "row_count": ["2", "5"]},
    ],
)
def test_reclamos_caso2_no_inventa_ceros_con_datos_desconocidos(monkeypatch, columns):
    leer(monkeypatch, pl.DataFrame(columns))
    assert "c2" not in by_id(rout_parte2.calcular_desde_resumen("claims", None))


def test_emergencias_caso5_cuenta_bicis_y_publica_el_tiempo_de_resolucion(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP] * 3,
                "causaTipo": ["MOVILIDAD_BICICLETA", "RECLAMO", None],
                "cantidadEmergencias": [3, 2, 100],
                "criticidadAfectada": [0, 0, 0],
                "tiempoPromResolucion": [866.016, 910.7, 863.6],
            }
        ),
    )
    datos = by_id(rout_parte2.calcular_desde_resumen("emergencies", None))
    assert datos["c5"].valor == 3
    assert datos["c5b"].valor == 866.0
    assert datos["c5b"].unidad == "min"
    assert datos["c2"].valor == 2  # lo existente no cambia


def test_emergencias_sin_tiempo_de_resolucion_no_inventa_c5b(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP],
                "causaTipo": ["MOVILIDAD_BICICLETA"],
                "cantidadEmergencias": [1],
                "tiempoPromResolucion": [None],
            },
            schema_overrides={"tiempoPromResolucion": pl.Float64},
        ),
    )
    datos = by_id(rout_parte2.calcular_desde_resumen("emergencies", None))
    assert datos["c5"].valor == 1
    assert "c5b" not in datos


def test_reclamos_caso5_compara_emergencia_contra_otras_causas(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP] * 4,
                "causaTipo": ["EMERGENCIA", "EVENTO_CLIMATICO", None, "RESERVA"],
                "row_count": [1, 7, 12, 7],
            }
        ),
    )
    datos = by_id(rout_parte2.calcular_desde_resumen("claims", None))
    assert datos["c5"].valor == 1
    assert [(d.etiqueta, d.valor) for d in datos["c5"].detalle] == [("Otras causas", 26)]
    assert datos["c1"].valor == 7 and datos["c6"].valor == 7  # lo existente no cambia


def test_movilidad_caso5_viajes_interrumpidos_contra_normales(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP] * 3,
                "causaTipo": ["EMERGENCIA", "INCIDENTE_VIAL", "NORMAL"],
                "cantidadAfectaciones": [21, 12, 0],
                "cantidadViajesInterrumpidos": [2, 12, 36],
            }
        ),
    )
    report = rout_parte2.calcular_desde_resumen("mobility", None)
    c5 = by_id(report)["c5"]
    assert c5.valor == 2
    assert [(d.etiqueta, d.valor) for d in c5.detalle] == [("Viajes finalizados normalmente", 36)]
    graficos = {g.id: g for g in report.resumen_gold}
    assert set(graficos) == {"mobility-stations", "mobility-interruptions"}
    grafico = graficos["mobility-interruptions"]
    assert {p.etiqueta: p.valor for p in grafico.puntos} == {
        "Operación normal": 36,
        "Incidente vial": 12,
        "Emergencia": 2,
    }


def test_residuos_caso5_y_grafico_por_causa(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP] * 5,
                "estado_actual": ["PROGRAMADA", "PROGRAMADA", "AFECTADA", "PROGRAMADA", "AFECTADA"],
                "causaTipo": ["EMERGENCIA", "EVENTO_PUBLICO", "EVENTO_PUBLICO", None, None],
                "cantidadIntervenciones": [1, 13, 14, 35, 6],
                "cantidadAfectadas": [0, 0, 14, 0, 6],
            }
        ),
    )
    report = rout_parte2.calcular_desde_resumen("waste", None)
    assert by_id(report)["c5"].valor == 1
    [grafico] = report.resumen_gold
    assert grafico.id == "waste-cause"
    assert grafico.fecha_snapshot == SNAP
    assert [(p.etiqueta, p.valor) for p in grafico.puntos] == [
        ("Operación normal", 41),
        ("Evento público", 27),
        ("Emergencia", 1),
    ]


def test_espacios_caso5_accidente_vial_y_version_que_pide_el_front(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP] * 4,
                "causaTipo": ["ACCIDENTE_VIAL", "ACCIDENTE_VIAL", "EVENTO_CLIMATICO", None],
                "cantidadActividades": [2, 10, 38, 41],
            }
        ),
    )
    report = rout_parte2.calcular_desde_resumen("culture", None)
    assert report.version_cultura == 2
    assert by_id(report)["c5"].valor == 12
    [grafico] = report.resumen_gold
    assert grafico.id == "culture-cause"
    # las actividades sin causa no son una "causa publicada"
    assert {p.etiqueta: p.valor for p in grafico.puntos} == {"Clima": 38, "Accidente vial": 12}


def test_grafico_omite_causas_vacias(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP] * 2,
                "causaTipo": ["", "EMERGENCIA"],
                "cantidadIntervenciones": [3, 1],
            }
        ),
    )
    [grafico] = rout_parte2.calcular_desde_resumen("waste", None).resumen_gold
    assert [p.etiqueta for p in grafico.puntos] == ["Emergencia"]


def test_reporte_de_espacios_con_feed_conserva_los_graficos_de_gold(monkeypatch):
    from app.services.parte2_events import Part2Events

    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP],
                "causaTipo": ["ACCIDENTE_VIAL"],
                "cantidadActividades": [12],
            }
        ),
    )
    feed = Part2Events.model_validate(
        {
            "actualizado_en": "2026-11-17T15:00:00Z",
            "cobertura": ["culture"],
            "eventos": [
                {
                    "metadata": {"eventId": "1", "eventType": "ActividadModificada"},
                    "data": {"actividadId": "a", "causaTipo": "ACCIDENTE_VIAL"},
                }
            ],
        }
    )
    monkeypatch.setattr(rout_parte2, "read_event_feed", lambda storage: feed)
    gold = rout_parte2.calcular_desde_resumen("culture", None)
    report = rout_parte2.report_from_events(None, "culture", gold)
    assert report.version_cultura == 2
    assert [g.id for g in report.resumen_gold] == ["culture-cause"]


# Caso 1 (evento climático) con las filas gold reales del 18/11.


def test_movilidad_caso1_estaciones_bloqueadas_por_clima(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP] * 3,
                "causaTipo": ["EVENTO_CLIMATICO", "RECLAMO", "NORMAL"],
                "cantidadAfectaciones": [17, 21, 0],
                "cantidadBloqueadas": [14, 6, 0],
                "estacionesBloqueadasDistintas": [12, 6, 0],
                "cantidadViajesInterrumpidos": [1, 0, 36],
            }
        ),
    )
    report = rout_parte2.calcular_desde_resumen("mobility", None)
    c1 = by_id(report)["c1"]
    assert c1.valor == 12
    assert [(d.etiqueta, d.valor) for d in c1.detalle] == [("Bloqueos registrados", 14)]
    estaciones = {g.id: g for g in report.resumen_gold}["mobility-stations"]
    assert [(p.etiqueta, p.valor) for p in estaciones.puntos] == [("Reclamo", 21), ("Clima", 17)]


def test_movilidad_sin_columnas_de_bloqueo_no_inventa_c1(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP],
                "causaTipo": ["EVENTO_CLIMATICO"],
                "cantidadAfectaciones": [17],
            }
        ),
    )
    assert "c1" not in by_id(rout_parte2.calcular_desde_resumen("mobility", None))


def test_residuos_caso1_usa_la_causa_de_la_afectacion(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP] * 4,
                "causaTipo": ["EVENTO_PUBLICO", "RECLAMO", None, "RESERVA"],
                "causaTipoAfectacion": [
                    "EVENTO_CLIMATICO",
                    "EVENTO_CLIMATICO",
                    None,
                    "INCIDENTE_VIAL",
                ],
                "cantidadIntervenciones": [3, 1, 35, 2],
                "cantidadAfectadas": [3, 1, 0, 2],
            }
        ),
    )
    report = rout_parte2.calcular_desde_resumen("waste", None)
    assert by_id(report)["c1"].valor == 4


def test_residuos_sin_causa_de_afectacion_no_inventa_c1(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP],
                "causaTipo": ["EVENTO_CLIMATICO"],
                "cantidadIntervenciones": [3],
                "cantidadAfectadas": [3],
            }
        ),
    )
    assert "c1" not in by_id(rout_parte2.calcular_desde_resumen("waste", None))


def test_espacios_caso1_culturales_canceladas_o_suspendidas_por_clima(monkeypatch):
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP] * 6,
                "estado_actual": [
                    "CANCELADA",
                    "SUSPENDIDA",
                    "CANCELADA",
                    "PROGRAMADA",
                    "CANCELADA",
                    "CANCELADA",
                ],
                "categoria": [
                    "CULTURAL",
                    "CULTURAL",
                    "DEPORTIVO",
                    "Talleres",
                    "Música",
                    "CULTURAL",
                ],
                "causaTipo": [
                    "EVENTO_CLIMATICO",
                    "EVENTO_CLIMATICO",
                    "EVENTO_CLIMATICO",
                    "EVENTO_CLIMATICO",
                    "EVENTO_CLIMATICO",
                    "RECLAMO",
                ],
                "cantidadActividades": [24, 6, 3, 1, 1, 5],
            }
        ),
    )
    c1 = by_id(rout_parte2.calcular_desde_resumen("culture", None))["c1"]
    assert c1.valor == 30
    assert [(d.etiqueta, d.valor) for d in c1.detalle] == [("Todas las categorías", 34)]


def test_residuos_con_causa_programacion_y_origen(monkeypatch):
    """Gold renombro causaTipo -> causaProgramacion (18/11) y separa el caso 5
    por origenProgramacion: los indicadores no deben quedar vacios."""
    leer(
        monkeypatch,
        pl.DataFrame(
            {
                "fecha_snapshot": [SNAP] * 4,
                "estado_actual": ["PROGRAMADA", "AFECTADA", "AFECTADA", "PROGRAMADA"],
                "causaProgramacion": ["EVENTO_PUBLICO", "RESERVA", None, None],
                "causaTipoAfectacion": [None, "EVENTO_CLIMATICO", "INCIDENTE_VIAL", None],
                "origenProgramacion": ["NINGUNO", "NINGUNO", "EMERGENCIA", "ALERTA"],
                "cantidadIntervenciones": [5, 3, 2, 4],
                "cantidadAfectadas": [0, 3, 2, 0],
            }
        ),
    )
    report = rout_parte2.calcular_desde_resumen("waste", None)
    indicadores = by_id(report)
    assert indicadores["c1"].valor == 3
    assert indicadores["c5"].valor == 2
    [grafico] = report.resumen_gold
    assert grafico.id == "waste-cause"
    assert sum(p.valor for p in grafico.puntos) == 14
