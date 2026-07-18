"""JSON API checks with simple dot-path assertions."""

from __future__ import annotations

import json
from typing import Any

import httpx

from ..models import CheckResult, JsonMonitor
from .base import Timer, result
from .http import request_web

MISSING = object()


def resolve_path(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return MISSING
    return current


def assert_value(actual: Any, assertion: str, expected: Any) -> bool:
    if assertion == "exists":
        return actual is not MISSING
    if actual is MISSING:
        return False
    if assertion == "equals":
        return actual == expected
    if assertion == "not_equals":
        return actual != expected
    if assertion in {"greater_than", "less_than"}:
        if isinstance(actual, bool) or isinstance(expected, bool):
            raise TypeError("valores booleanos não são comparáveis numericamente")
        if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
            raise TypeError("a assertiva requer valores numéricos")
        return actual > expected if assertion == "greater_than" else actual < expected
    raise ValueError("assertiva desconhecida")


async def check_json(
    monitor: JsonMonitor,
    timeout: float,
    client: httpx.AsyncClient,
) -> CheckResult:
    timer = Timer()
    try:
        response, body, timer = await request_web(monitor, timeout, client)
        if response.status_code not in monitor.expected_status:
            return result(
                monitor.id,
                False,
                f"HTTP {response.status_code}",
                timer=timer,
                error_code="unexpected_status",
            )
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return result(
                monitor.id, False, "Resposta JSON inválida", timer=timer, error_code="invalid_json"
            )
        actual = resolve_path(payload, monitor.json_path)
        if actual is MISSING:
            return result(
                monitor.id,
                False,
                f"Caminho JSON ausente: {monitor.json_path}",
                timer=timer,
                error_code="json_path_missing",
            )
        try:
            success = assert_value(actual, monitor.assertion, monitor.expected_value)
        except TypeError as exc:
            return result(monitor.id, False, str(exc), timer=timer, error_code="type_mismatch")
        return result(
            monitor.id,
            success,
            "Assertiva JSON atendida" if success else "Assertiva JSON não atendida",
            timer=timer,
            error_code=None if success else "assertion_failed",
            metadata={"json_path": monitor.json_path, "assertion": monitor.assertion},
        )
    except httpx.TimeoutException:
        return result(monitor.id, False, "Tempo limite excedido", timer=timer, error_code="timeout")
    except httpx.HTTPError as exc:
        return result(monitor.id, False, str(exc), timer=timer, error_code="http_error")
