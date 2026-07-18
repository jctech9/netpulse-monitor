"""Incident lifecycle helpers."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any


def incident_id(monitor_id: str, started_at: str) -> str:
    digest = hashlib.sha256(f"{monitor_id}:{started_at}".encode()).hexdigest()[:12]
    return f"inc_{digest}"


def open_incident(
    incidents: list[dict[str, Any]], monitor_id: str, started_at: str, cause: str
) -> dict[str, Any]:
    existing = next(
        (
            item
            for item in incidents
            if item["monitor_id"] == monitor_id and item["ended_at"] is None
        ),
        None,
    )
    if existing:
        return existing
    incident = {
        "id": incident_id(monitor_id, started_at),
        "monitor_id": monitor_id,
        "started_at": started_at,
        "ended_at": None,
        "cause": cause,
        "duration_seconds": None,
        "status": "open",
        "message": "Estamos investigando uma indisponibilidade confirmada.",
    }
    incidents.append(incident)
    return incident


def close_incident(
    incidents: list[dict[str, Any]], monitor_id: str, ended_at: str
) -> dict[str, Any] | None:
    incident = next(
        (
            item
            for item in incidents
            if item["monitor_id"] == monitor_id and item["ended_at"] is None
        ),
        None,
    )
    if not incident:
        return None
    started = datetime.fromisoformat(incident["started_at"].replace("Z", "+00:00"))
    ended = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    incident.update(
        {
            "ended_at": ended_at,
            "duration_seconds": max(0, int((ended - started).total_seconds())),
            "status": "resolved",
            "message": "O serviço foi normalizado e permanece em observação.",
        }
    )
    return incident


def prune_incidents(
    incidents: list[dict[str, Any]], now: datetime, retention_days: int
) -> list[dict[str, Any]]:
    cutoff = now.astimezone(UTC) - timedelta(days=retention_days)
    return [
        item
        for item in incidents
        if item.get("ended_at") is None
        or datetime.fromisoformat(item["ended_at"].replace("Z", "+00:00")) >= cutoff
    ]
