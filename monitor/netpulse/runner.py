"""Concurrency-limited monitor runner."""

from __future__ import annotations

import asyncio

import httpx

from .checks import check_dns, check_http, check_json, check_keyword, check_tcp, check_tls
from .models import (
    AppConfig,
    CheckResult,
    DnsMonitor,
    HttpMonitor,
    JsonMonitor,
    KeywordMonitor,
    Monitor,
    TcpMonitor,
    TlsMonitor,
)


async def run_checks(config: AppConfig) -> list[CheckResult]:
    semaphore = asyncio.Semaphore(config.settings.max_concurrency)
    limits = httpx.Limits(
        max_connections=config.settings.max_concurrency,
        max_keepalive_connections=config.settings.max_concurrency,
    )
    async with httpx.AsyncClient(limits=limits, verify=True) as client:

        async def run_one(monitor: Monitor) -> CheckResult:
            async with semaphore:
                timeout = monitor.timeout_seconds or config.settings.default_timeout_seconds
                if isinstance(monitor, HttpMonitor):
                    return await check_http(monitor, timeout, client)
                if isinstance(monitor, KeywordMonitor):
                    return await check_keyword(monitor, timeout, client)
                if isinstance(monitor, JsonMonitor):
                    return await check_json(monitor, timeout, client)
                if isinstance(monitor, TcpMonitor):
                    return await check_tcp(monitor, timeout)
                if isinstance(monitor, DnsMonitor):
                    return await check_dns(monitor, timeout)
                if isinstance(monitor, TlsMonitor):
                    return await check_tls(monitor, timeout)
                raise TypeError(f"Tipo de monitor não suportado: {monitor.type}")

        return await asyncio.gather(*(run_one(item) for item in config.monitors if item.enabled))
