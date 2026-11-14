from datetime import date

import polars as pl

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
    assert values == {"c1": 2, "c2": 3, "c6": 0}
    assert report.datos[0].detalle[0].valor == 8


def test_old_snapshot_without_cause_stays_pending(monkeypatch):
    monkeypatch.setattr(
        rout_parte2.AzureParquetRepository,
        "read",
        lambda self, path: pl.DataFrame({"row_count": [10]}),
    )
    assert rout_parte2.calcular_desde_resumen("claims", None).datos == []
