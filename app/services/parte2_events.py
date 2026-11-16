from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field


class EventMetadata(BaseModel):
    eventId: str = Field(min_length=1)
    eventType: str = Field(min_length=1)


class EventEnvelope(BaseModel):
    metadata: EventMetadata
    data: dict


class Part2Events(BaseModel):
    actualizado_en: AwareDatetime
    cobertura: set[Literal["culture", "emergencies"]] = Field(default_factory=set)
    eventos: list[EventEnvelope]
    casos_por_referencia: dict[str, Annotated[int, Field(ge=1, le=6)]] = Field(default_factory=dict)


class ContextImpact(BaseModel):
    caso: int | None
    origen: str
    emergencias: int
    ultimo_vinculo: datetime


def identifier(data: dict, key: str) -> str | None:
    value = data.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def culture_counts(feed: Part2Events) -> dict[str, tuple[int, list[tuple[str, int]]]]:
    created = {}
    cancellations = set()
    modified = set()
    claim_spaces = set()
    incident_spaces = set()
    seen_events = set()
    for event in feed.eventos:
        if event.metadata.eventId in seen_events:
            continue
        seen_events.add(event.metadata.eventId)
        event_type = event.metadata.eventType.removeprefix("com.citypass.espacios.")
        data = event.data
        activity = identifier(data, "actividadId") or identifier(data, "eventoId")
        cause = data.get("causaTipo")
        if event_type == "ActividadCreada" and activity:
            created.setdefault(activity, data)
        elif event_type == "EspacioPublicoAfectado":
            space = identifier(data, "espacioId")
            if space and cause == "RECLAMO":
                claim_spaces.add(space)
            if space and cause == "INCIDENTE_VIAL":
                incident_spaces.add(space)
        elif activity:
            cancelled = event_type in {"ActividadCancelada", "EventoCancelado"} or (
                event_type == "ActividadModificada"
                and data.get("estadoNuevo") in ("CANCELADA", "CANCELADO")
            )
            if cancelled and cause == "EVENTO_CLIMATICO":
                cancellations.add(activity)
            if event_type == "ActividadModificada" and cause == "ACCIDENTE_VIAL":
                modified.add(activity)

    return {
        "c1": (len(cancellations), []),
        "c2": (len(claim_spaces), []),
        "c3": (
            sum(
                type(row.get("capacidad")) is int and row["capacidad"] >= 500
                for row in created.values()
            ),
            [],
        ),
        "c4": (len(incident_spaces), []),
        "c5": (len(modified), []),
        "c6": (
            sum(
                row.get("organizadorTipo") in ("CIUDADANO", "CIUADANO") for row in created.values()
            ),
            [
                (
                    "Organizadas por la ciudad",
                    sum(row.get("organizadorTipo") == "CIUDAD" for row in created.values()),
                ),
                ("Actividades totales", len(created)),
            ],
        ),
    }


class PublicEventImpact(BaseModel):
    evento_id: str
    emergencias: int
    ultimo_vinculo: datetime


def public_event_impacts(feed: Part2Events) -> list[PublicEventImpact]:
    grouped: dict[str, dict[str, datetime]] = {}
    for event in feed.eventos:
        if event.metadata.eventType != "com.citypass.emergencias.EmergenciaVinculadaAContextoZona":
            continue
        data = event.data
        reference = identifier(data, "referenciaExterna")
        emergency = identifier(data, "emergenciaId")
        linked = identifier(data, "vinculadaEn")
        if (
            not (reference and emergency and linked and identifier(data, "contextoId"))
            or data.get("backfill") is not False
            or data.get("contextoOrigen") != "espacios"
            or data.get("contextoTipo") != "EVENTO_ESPACIO_PUBLICO"
        ):
            continue
        try:
            instant = datetime.fromisoformat(linked)
        except ValueError:
            continue
        if instant.utcoffset() is None:
            continue
        entries = grouped.setdefault(reference, {})
        entries[emergency] = max(entries.get(emergency, instant), instant)
    return sorted(
        [
            PublicEventImpact(
                evento_id=reference,
                emergencias=len(entries),
                ultimo_vinculo=max(entries.values()).astimezone(UTC),
            )
            for reference, entries in grouped.items()
        ],
        key=lambda impact: (impact.ultimo_vinculo, impact.evento_id),
        reverse=True,
    )


def context_impacts(feed: Part2Events) -> list[ContextImpact]:
    groups: dict[tuple[int | None, str], dict[str, datetime]] = {}
    for event in feed.eventos:
        if event.metadata.eventType != "com.citypass.emergencias.EmergenciaVinculadaAContextoZona":
            continue
        data = event.data
        emergency = identifier(data, "emergenciaId")
        origin = identifier(data, "contextoOrigen")
        value = identifier(data, "vinculadaEn")
        context = identifier(data, "contextoId")
        if not (emergency and context and origin and value) or data.get("backfill") is not False:
            continue
        try:
            linked_at = datetime.fromisoformat(value)
        except ValueError:
            continue
        if linked_at.utcoffset() is None:
            continue
        reference = identifier(data, "referenciaExterna")
        case = feed.casos_por_referencia.get(reference or "")
        emergencies = groups.setdefault((case, origin), {})
        emergencies[emergency] = max(emergencies.get(emergency, linked_at), linked_at)

    return [
        ContextImpact(
            caso=case,
            origen=origin,
            emergencias=len(emergencies),
            ultimo_vinculo=max(emergencies.values()).astimezone(UTC),
        )
        for (case, origin), emergencies in groups.items()
    ]
