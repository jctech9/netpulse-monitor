"""Bounded HTTP/HTTPS checks with TLS validation always enabled."""

from __future__ import annotations

import asyncio

import httpx

from ..models import CheckResult, HttpMonitor, WebMonitor
from .base import Timer, result

MAX_BODY_BYTES = 512_000
TRANSIENT_ERRORS = (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)


async def request_web(
    monitor: WebMonitor,
    timeout: float,
    client: httpx.AsyncClient,
) -> tuple[httpx.Response, bytes, Timer]:
    timer = Timer()
    last_error: Exception | None = None
    for attempt in range(monitor.retries + 1):
        try:
            async with client.stream(
                monitor.method,
                monitor.url,
                timeout=httpx.Timeout(timeout),
                follow_redirects=monitor.follow_redirects,
                headers={
                    "User-Agent": "NetPulse-Monitor/1.0 (+https://github.com/jctech9/netpulse-monitor)"
                },
            ) as response:
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    remaining = MAX_BODY_BYTES - len(body)
                    if remaining <= 0:
                        break
                    body.extend(chunk[:remaining])
                return response, bytes(body), timer
        except TRANSIENT_ERRORS as exc:
            last_error = exc
            if attempt < monitor.retries:
                await asyncio.sleep(0.15 * (attempt + 1))
    assert last_error is not None
    raise last_error


async def check_http(
    monitor: HttpMonitor,
    timeout: float,
    client: httpx.AsyncClient,
) -> CheckResult:
    timer = Timer()
    try:
        response, _, timer = await request_web(monitor, timeout, client)
        success = response.status_code in monitor.expected_status
        return result(
            monitor.id,
            success,
            f"HTTP {response.status_code}",
            timer=timer,
            error_code=None if success else "unexpected_status",
            metadata={"status_code": response.status_code},
        )
    except httpx.TimeoutException:
        return result(monitor.id, False, "Tempo limite excedido", timer=timer, error_code="timeout")
    except httpx.HTTPError as exc:
        return result(monitor.id, False, str(exc), timer=timer, error_code="http_error")
