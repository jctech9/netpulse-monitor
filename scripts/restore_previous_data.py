"""Restore state from the published site first, then an Actions cache backup."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCHEMA_VERSION = 1


def fetch_json(url: str) -> dict[str, Any]:
    separator = "&" if "?" in url else "?"
    request = Request(
        f"{url}{separator}v={int(time.time())}",
        headers={"User-Agent": "NetPulse-Restore/1.0", "Cache-Control": "no-cache"},
    )
    with urlopen(request, timeout=12) as response:
        if response.length and response.length > 5_000_000:
            raise ValueError("arquivo remoto excede o limite")
        data = json.loads(response.read(5_000_001))
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("schema público incompatível")
    return data


def state_from_public(
    status: dict[str, Any], history: dict[str, Any], incidents: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(status.get("monitors"), list):
        raise ValueError("status.monitors inválido")
    if not isinstance(history.get("monitors"), dict):
        raise ValueError("history.monitors inválido")
    if not isinstance(incidents.get("incidents"), list):
        raise ValueError("incidents.incidents inválido")
    monitor_states = {}
    for monitor in status["monitors"]:
        if not isinstance(monitor, dict) or not isinstance(monitor.get("id"), str):
            raise ValueError("monitor público inválido")
        monitor_states[monitor["id"]] = {
            "status": monitor.get("status", "unknown"),
            "consecutive_failures": 0,
            "consecutive_successes": 0,
            "config_fingerprint": None,
            "last_result": {
                "monitor_id": monitor["id"],
                "success": monitor.get("status") == "up",
                "status": monitor.get("status", "unknown"),
                "checked_at": monitor.get("last_checked_at"),
                "response_ms": monitor.get("response_ms"),
                "detail": monitor.get("detail", "Restaurado do site"),
                "error_code": None,
                "metadata": monitor.get("metadata", {}),
            },
        }
    return {
        "schema_version": 1,
        "updated_at": status.get("generated_at"),
        "monitors": monitor_states,
        "history": history["monitors"],
        "incidents": incidents["incidents"],
        "pending_events": [],
        "delivered_event_ids": [],
    }


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    temporary.replace(path)


def valid_cached_state(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("schema_version") == 1 and isinstance(data.get("monitors"), dict)
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-url", required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--cache-state", type=Path, required=True)
    args = parser.parse_args()
    base = args.site_url.rstrip("/") + "/data"
    try:
        status = fetch_json(f"{base}/status.json")
        history = fetch_json(f"{base}/history.json")
        incidents = fetch_json(f"{base}/incidents.json")
        atomic_write(args.state, state_from_public(status, history, incidents))
        print("Estado restaurado dos JSONs publicados.")
        return 0
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        print(f"Site anterior indisponível ou inválido: {type(exc).__name__}")
    if valid_cached_state(args.cache_state):
        args.state.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.cache_state, args.state)
        print("Estado restaurado do cache auxiliar.")
    else:
        print("Nenhum estado anterior válido; a primeira execução começará vazia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
