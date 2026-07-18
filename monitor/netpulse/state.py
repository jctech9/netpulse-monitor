"""Persistent state machine and atomic JSON handling."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .history import update_history
from .incidents import close_incident, open_incident, prune_incidents
from .models import AppConfig, CheckResult, Monitor
from .sanitization import sanitize_error, sanitize_metadata

STATE_SCHEMA_VERSION = 1


def isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def empty_state() -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "updated_at": None,
        "monitors": {},
        "history": {},
        "incidents": [],
        "pending_events": [],
        "delivered_event_ids": [],
    }


def validate_state(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and data.get("schema_version") == STATE_SCHEMA_VERSION
        and isinstance(data.get("monitors"), dict)
        and isinstance(data.get("history"), dict)
        and isinstance(data.get("incidents"), list)
        and isinstance(data.get("pending_events"), list)
    )


def load_state(path: str | Path) -> tuple[dict[str, Any], bool]:
    state_path = Path(path)
    if not state_path.exists():
        return empty_state(), False
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_state(), True
    if not validate_state(data):
        return empty_state(), True
    data.setdefault("delivered_event_ids", [])
    return data, False


def atomic_write_json(path: str | Path, data: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Serialize before touching the existing target.
    encoded = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False, allow_nan=False)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as temporary:
            temporary.write(encoded)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        # Validate the exact bytes before the atomic replace.
        json.loads(Path(temporary_name).read_text(encoding="utf-8"))
        os.replace(temporary_name, target)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def config_fingerprint(monitor: Monitor) -> str:
    payload = monitor.model_dump(mode="json", exclude={"name", "group", "description"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def event_id(kind: str, monitor_id: str, timestamp: str) -> str:
    return hashlib.sha256(f"{kind}:{monitor_id}:{timestamp}".encode()).hexdigest()[:20]


def enqueue_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    known = set(state.get("delivered_event_ids", []))
    known.update(item["id"] for item in state.get("pending_events", []))
    if event["id"] not in known:
        state["pending_events"].append(event)


def _monitor_state() -> dict[str, Any]:
    return {
        "status": "unknown",
        "consecutive_failures": 0,
        "consecutive_successes": 0,
        "last_result": None,
        "config_fingerprint": None,
    }


def apply_result(
    state: dict[str, Any], monitor: Monitor, result: CheckResult, config: AppConfig
) -> None:
    item = state["monitors"].setdefault(monitor.id, _monitor_state())
    now_text = isoformat(result.checked_at)
    fingerprint = config_fingerprint(monitor)
    changed = item.get("config_fingerprint") not in {None, fingerprint}
    previous = item.get("status", "unknown")
    item["config_fingerprint"] = fingerprint

    if monitor.maintenance:
        item.update(status="maintenance", consecutive_failures=0, consecutive_successes=0)
    elif result.success and result.status == "degraded":
        item.update(status="degraded", consecutive_failures=0, consecutive_successes=0)
    elif result.success:
        item["consecutive_failures"] = 0
        item["consecutive_successes"] = item.get("consecutive_successes", 0) + 1
        recovery_threshold = (
            monitor.recovery_threshold or config.settings.default_recovery_threshold
        )
        if previous == "down" and item["consecutive_successes"] < recovery_threshold:
            item["status"] = "degraded"
        else:
            item["status"] = "up"
            if previous == "down":
                incident = close_incident(state["incidents"], monitor.id, now_text)
                if incident and monitor.notifications_enabled:
                    enqueue_event(
                        state,
                        {
                            "id": event_id("recovery", monitor.id, now_text),
                            "kind": "recovery",
                            "monitor_id": monitor.id,
                            "created_at": now_text,
                            "detail": result.detail,
                            "response_ms": result.response_ms,
                            "duration_seconds": incident["duration_seconds"],
                            "next_chunk": 0,
                        },
                    )
    else:
        item["consecutive_successes"] = 0
        item["consecutive_failures"] = item.get("consecutive_failures", 0) + 1
        failure_threshold = monitor.failure_threshold or config.settings.default_failure_threshold
        # A changed target must earn a fresh second sample before opening an incident.
        confirmed = item["consecutive_failures"] >= failure_threshold and not changed
        if previous == "down":
            item["status"] = "down"
        elif confirmed:
            item["status"] = "down"
            incident = open_incident(
                state["incidents"], monitor.id, now_text, sanitize_error(result.detail)
            )
            if monitor.notifications_enabled:
                enqueue_event(
                    state,
                    {
                        "id": event_id("down", monitor.id, incident["started_at"]),
                        "kind": "down",
                        "monitor_id": monitor.id,
                        "created_at": now_text,
                        "detail": result.detail,
                        "consecutive_failures": item["consecutive_failures"],
                        "next_chunk": 0,
                    },
                )
        else:
            item["status"] = "degraded"

    item["last_result"] = {
        "monitor_id": monitor.id,
        "success": result.success,
        "status": result.status,
        "checked_at": now_text,
        "response_ms": result.response_ms,
        "detail": sanitize_error(result.detail),
        "error_code": result.error_code,
        "metadata": sanitize_metadata(result.metadata),
    }
    sample = {
        "timestamp": now_text,
        "status": item["status"],
        "response_ms": result.response_ms,
    }
    update_history(
        state["history"],
        monitor.id,
        sample,
        now=result.checked_at,
        raw_hours=config.settings.raw_history_hours,
        hourly_days=config.settings.hourly_history_days,
    )


def update_state(
    state: dict[str, Any],
    config: AppConfig,
    results: list[CheckResult],
    now: datetime | None = None,
) -> dict[str, Any]:
    monitor_by_id = {monitor.id: monitor for monitor in config.monitors if monitor.enabled}
    for result in results:
        monitor = monitor_by_id.get(result.monitor_id)
        if monitor:
            apply_result(state, monitor, result, config)
    current = now or (max((result.checked_at for result in results), default=datetime.now(UTC)))
    state["updated_at"] = isoformat(current)
    state["incidents"] = prune_incidents(
        state["incidents"], current, config.settings.incident_retention_days
    )
    # Keep only active configuration while retaining history for retention/aggregation.
    state["monitors"] = {
        key: value for key, value in state["monitors"].items() if key in monitor_by_id
    }
    state["delivered_event_ids"] = state.get("delivered_event_ids", [])[-500:]
    return state
