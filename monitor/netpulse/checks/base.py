"""Shared check helpers."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from ..models import CheckResult
from ..sanitization import sanitize_error


class Timer:
    def __init__(self) -> None:
        self.started = time.perf_counter()

    @property
    def milliseconds(self) -> float:
        return round((time.perf_counter() - self.started) * 1000, 2)


def result(
    monitor_id: str,
    success: bool,
    detail: str,
    *,
    timer: Timer,
    status: str | None = None,
    error_code: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> CheckResult:
    return CheckResult(
        monitor_id=monitor_id,
        success=success,
        status=status or ("up" if success else "down"),
        checked_at=datetime.now(UTC),
        response_ms=timer.milliseconds,
        detail=sanitize_error(detail),
        error_code=error_code,
        metadata=metadata or {},
    )
