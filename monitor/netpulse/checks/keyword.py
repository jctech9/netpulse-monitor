"""Keyword/content checks without exposing response bodies."""

import httpx

from ..models import CheckResult, KeywordMonitor
from .base import Timer, result
from .http import request_web


async def check_keyword(
    monitor: KeywordMonitor,
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
        text = body.decode(response.encoding or "utf-8", errors="replace")
        haystack = text if monitor.case_sensitive else text.casefold()
        needle = monitor.keyword if monitor.case_sensitive else monitor.keyword.casefold()
        found = needle in haystack
        success = found if monitor.expectation == "present" else not found
        description = "Expressão encontrada" if found else "Expressão não encontrada"
        return result(
            monitor.id,
            success,
            description,
            timer=timer,
            error_code=None if success else "keyword_mismatch",
            metadata={"expectation": monitor.expectation},
        )
    except httpx.TimeoutException:
        return result(monitor.id, False, "Tempo limite excedido", timer=timer, error_code="timeout")
    except httpx.HTTPError as exc:
        return result(monitor.id, False, str(exc), timer=timer, error_code="http_error")
