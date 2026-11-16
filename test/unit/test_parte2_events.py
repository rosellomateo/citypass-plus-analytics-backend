from app.services.parte2_events import Part2Events, context_impacts, culture_counts


def feed(*events):
    return Part2Events.model_validate(
        {
            "actualizado_en": "2026-11-13T15:05:00Z",
            "cobertura": ["culture", "emergencies"],
            "casos_por_referencia": {"festival": 3},
            "eventos": [
                {"metadata": {"eventId": str(i), "eventType": event_type}, "data": data}
                for i, (event_type, data) in enumerate(events)
            ],
        }
    )


def test_culture_activity_rules_use_unique_ids_and_threshold():
    report = feed(
        ("ActividadCreada", {"actividadId": "a", "capacidad": 500, "organizadorTipo": "CIUADANO"}),
        ("ActividadCreada", {"actividadId": "b", "capacidad": 499, "organizadorTipo": "CIUDAD"}),
        ("ActividadCreada", {"actividadId": "a", "capacidad": 500, "organizadorTipo": "CIUADANO"}),
        ("ActividadCancelada", {"actividadId": "a", "causaTipo": "EVENTO_CLIMATICO"}),
        ("ActividadModificada", {"actividadId": "b", "causaTipo": "ACCIDENTE_VIAL"}),
        ("ActividadModificada", {"actividadId": "b", "causaTipo": "ACCIDENTE_VIAL"}),
        ("ActividadModificada", {"actividadId": "b", "causaTipo": "EVENTO_CLIMATICO"}),
        ("EspacioPublicoAfectado", {"espacioId": "p", "causaTipo": "RECLAMO"}),
        ("EspacioPublicoAfectado", {"espacioId": "p", "causaTipo": "RECLAMO"}),
        ("EspacioPublicoAfectado", {"espacioId": "p", "causaTipo": "INCIDENTE_VIAL"}),
    )

    values = culture_counts(report)
    assert {code: count for code, (count, _) in values.items()} == dict.fromkeys(
        ["c1", "c2", "c3", "c4", "c5", "c6"], 1
    )
    assert values["c6"][1] == [("Organizadas por la ciudad", 1), ("Actividades totales", 2)]


def test_context_impact_uses_explicit_scenario_and_excludes_backfill():
    event_type = "com.citypass.emergencias.EmergenciaVinculadaAContextoZona"
    data = {
        "emergenciaId": "e1",
        "contextoId": "z1",
        "contextoOrigen": "espacios",
        "referenciaExterna": "festival",
        "vinculadaEn": "2026-11-13T15:01:16.198Z",
        "backfill": False,
    }

    result = context_impacts(
        feed(
            (event_type, data),
            (event_type, {**data, "contextoId": "z2"}),
            (event_type, {**data, "emergenciaId": "e2", "backfill": True}),
            (event_type, {**data, "emergenciaId": "e3", "referenciaExterna": "otra"}),
        )
    )

    assert [(impact.caso, impact.emergencias) for impact in result] == [(3, 1), (None, 1)]


def test_report_loads_latest_complete_events_from_configured_blob(monkeypatch):
    from app.routers import rout_parte2

    previous = rout_parte2.IndicadoresParteDos(
        actualizado_en="2026-11-13T15:01:00Z",
        version_cultura=2,
        datos=[rout_parte2.Indicador(id="c3", valor=0)],
    )
    current = feed(
        (
            "ActividadCreada",
            {"actividadId": "festival", "capacidad": 500, "organizadorTipo": "CIUDAD"},
        ),
    )
    monkeypatch.setenv("PART2_EVENTS_BLOB", "demo/escenarios.json")

    def read(_, path):
        assert path == "demo/escenarios.json"
        return current.model_dump()

    monkeypatch.setattr(rout_parte2.AzureJsonRepository, "read", read)
    updated = rout_parte2.report_from_events(None, "culture", previous)
    assert updated.actualizado_en == current.actualizado_en
    assert next(item.valor for item in updated.datos if item.id == "c3") == 1

    current.cobertura.clear()
    assert rout_parte2.report_from_events(None, "culture", previous) == previous


def test_reads_team_endpoint_when_configured(monkeypatch):
    from io import BytesIO

    from app.routers import rout_parte2

    sample = feed()
    monkeypatch.setenv("PART2_EVENTS_URL", "https://events.example.test/corte")
    calls = []

    def open_endpoint(url, timeout):
        calls.append((url, timeout))
        return BytesIO(sample.model_dump_json().encode())

    monkeypatch.setattr(rout_parte2, "urlopen", open_endpoint)
    assert rout_parte2.read_event_feed(None) == sample
    assert calls == [("https://events.example.test/corte", 5)]


def test_public_event_reference_counts_unique_emergencies_without_backfill():
    from app.services.parte2_events import public_event_impacts

    event_type = "com.citypass.emergencias.EmergenciaVinculadaAContextoZona"
    link = {
        "emergenciaId": "e1",
        "contextoId": "z1",
        "contextoOrigen": "espacios",
        "contextoTipo": "EVENTO_ESPACIO_PUBLICO",
        "referenciaExterna": "festival",
        "vinculadaEn": "2026-11-13T15:01:16Z",
        "backfill": False,
    }
    data = feed(
        (event_type, link),
        (event_type, {**link, "contextoId": "z2"}),
        (event_type, {**link, "emergenciaId": "e2"}),
        (event_type, {**link, "emergenciaId": "historica", "backfill": True}),
        (event_type, {**link, "emergenciaId": "climatica", "contextoTipo": "ALERTA_CLIMATICA"}),
    )
    assert [(row.evento_id, row.emergencias) for row in public_event_impacts(data)] == [
        ("festival", 2)
    ]
