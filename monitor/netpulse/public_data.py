"""Build the three sanitized public JSON documents."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .history import availability, availability_30d, period_samples
from .models import AppConfig, Monitor
from .sanitization import sanitize_error, sanitize_metadata, sanitize_url
from .state import atomic_write_json, isoformat

PUBLIC_SCHEMA_VERSION = 1


def target_for(monitor: Monitor) -> str:
    if hasattr(monitor, "url"):
        return sanitize_url(monitor.url)
    host = getattr(monitor, "host", "")
    port = getattr(monitor, "port", None)
    return f"{host}:{port}" if port else host


def overall_status(statuses: list[str]) -> str:
    active = [status for status in statuses if status != "maintenance"]
    if not active or all(status == "unknown" for status in active):
        return "unknown"
    known = [status for status in active if status != "unknown"]
    if known and all(status == "down" for status in known) and len(known) == len(active):
        return "major_outage"
    if any(status in {"down", "degraded", "unknown"} for status in active):
        return "degraded"
    return "operational"


def build_public_data(
    state: dict[str, Any], config: AppConfig, *, demo: bool = False
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    generated = state.get("updated_at") or isoformat(datetime.now(UTC))
    now = datetime.fromisoformat(generated.replace("Z", "+00:00"))
    monitors: list[dict[str, Any]] = []
    statuses: list[str] = []
    for monitor in config.monitors:
        if not monitor.enabled:
            continue
        current = state.get("monitors", {}).get(monitor.id, {})
        status = current.get("status", "unknown")
        statuses.append(status)
        last = current.get("last_result") or {}
        bucket = state.get("history", {}).get(monitor.id, {"raw": [], "hourly": []})
        last_24h = period_samples(bucket, now, 24)
        monitors.append(
            {
                "id": monitor.id,
                "name": monitor.name,
                "group": monitor.group,
                "type": monitor.type,
                "description": sanitize_error(monitor.description),
                "target": target_for(monitor),
                "status": status,
                "response_ms": last.get("response_ms"),
                "last_checked_at": last.get("checked_at"),
                "detail": sanitize_error(last.get("detail", "Aguardando primeira verificação")),
                "uptime_24h": availability(last_24h),
                "uptime_30d": availability_30d(bucket),
                "metadata": sanitize_metadata(last.get("metadata", {})),
            }
        )
    counts = Counter(statuses)
    eligible = [
        sample
        for bucket in state.get("history", {}).values()
        for sample in period_samples(bucket, now, 24)
    ]
    global_uptime = availability(eligible)
    incidents = [sanitize_metadata(item) for item in state.get("incidents", [])]
    status_document = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "generated_at": generated,
        "last_successful_update": generated,
        "timezone": config.settings.timezone,
        "demo": demo,
        "overall_status": overall_status(statuses),
        "overall_uptime_24h": global_uptime,
        "counts": {
            status: counts.get(status, 0)
            for status in ("up", "degraded", "down", "maintenance", "unknown")
        },
        "open_incidents": sum(item.get("status") == "open" for item in incidents),
        "monitors": monitors,
    }
    history_document = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "generated_at": generated,
        "demo": demo,
        "monitors": sanitize_metadata(state.get("history", {})),
    }
    incidents_document = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "generated_at": generated,
        "demo": demo,
        "incidents": sorted(incidents, key=lambda item: item["started_at"], reverse=True),
    }
    return status_document, history_document, incidents_document


def write_public_data(
    output: str | Path, state: dict[str, Any], config: AppConfig, *, demo: bool = False
) -> None:
    output_path = Path(output)
    status, history, incidents = build_public_data(state, config, demo=demo)
    atomic_write_json(output_path / "status.json", status)
    atomic_write_json(output_path / "history.json", history)
    atomic_write_json(output_path / "incidents.json", incidents)
