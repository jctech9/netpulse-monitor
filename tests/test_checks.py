import asyncio
import socket
import ssl

import httpx
import pytest
from netpulse.checks.dns import check_dns
from netpulse.checks.http import check_http
from netpulse.checks.json_api import check_json
from netpulse.checks.keyword import check_keyword
from netpulse.checks.tcp import check_tcp
from netpulse.checks.tls import check_tls
from netpulse.models import (
    DnsMonitor,
    HttpMonitor,
    JsonMonitor,
    KeywordMonitor,
    TcpMonitor,
    TlsMonitor,
)


def client_with(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_http_healthy_and_unexpected() -> None:
    monitor = HttpMonitor(
        id="http_check", name="HTTP", group="Web", type="http", url="https://example.com"
    )
    async with client_with(lambda request: httpx.Response(200, text="ok")) as client:
        result = await check_http(monitor, 1, client)
    assert result.success and result.detail == "HTTP 200"

    async with client_with(lambda request: httpx.Response(503, text="bad")) as client:
        result = await check_http(monitor, 1, client)
    assert not result.success and result.error_code == "unexpected_status"


@pytest.mark.asyncio
async def test_http_timeout() -> None:
    def timeout(request):
        raise httpx.ReadTimeout("timed out", request=request)

    monitor = HttpMonitor(
        id="http_check", name="HTTP", group="Web", type="http", url="https://example.com", retries=0
    )
    async with client_with(timeout) as client:
        result = await check_http(monitor, 0.01, client)
    assert result.error_code == "timeout"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "expectation", "success"),
    [
        ("NetPulse is ready", "present", True),
        ("Nothing here", "present", False),
        ("Nothing here", "absent", True),
    ],
)
async def test_keyword(body: str, expectation: str, success: bool) -> None:
    monitor = KeywordMonitor(
        id="keyword_check",
        name="Keyword",
        group="Web",
        type="keyword",
        url="https://example.com",
        keyword="NetPulse",
        expectation=expectation,
    )
    async with client_with(lambda request: httpx.Response(200, text=body)) as client:
        result = await check_keyword(monitor, 1, client)
    assert result.success is success


@pytest.mark.asyncio
async def test_json_valid_invalid_and_missing() -> None:
    monitor = JsonMonitor(
        id="json_check",
        name="JSON",
        group="API",
        type="json",
        url="https://example.com",
        json_path="current.value",
        assertion="greater_than",
        expected_value=10,
    )
    async with client_with(
        lambda request: httpx.Response(200, json={"current": {"value": 12}})
    ) as client:
        assert (await check_json(monitor, 1, client)).success
    async with client_with(lambda request: httpx.Response(200, text="not json")) as client:
        assert (await check_json(monitor, 1, client)).error_code == "invalid_json"
    async with client_with(lambda request: httpx.Response(200, json={"other": 1})) as client:
        assert (await check_json(monitor, 1, client)).error_code == "json_path_missing"


@pytest.mark.asyncio
async def test_tcp_success_and_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    class Writer:
        def close(self):
            self.closed = True

        async def wait_closed(self):
            return None

    async def connected(*args, **kwargs):
        return object(), Writer()

    monitor = TcpMonitor(
        id="tcp_check", name="TCP", group="Infra", type="tcp", host="example.com", port=443
    )
    monkeypatch.setattr(asyncio, "open_connection", connected)
    assert (await check_tcp(monitor, 1)).success

    async def refused(*args, **kwargs):
        raise ConnectionRefusedError("closed")

    monkeypatch.setattr(asyncio, "open_connection", refused)
    assert (await check_tcp(monitor, 1)).error_code == "connection_failed"


@pytest.mark.asyncio
async def test_dns_success_and_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monitor = DnsMonitor(id="dns_check", name="DNS", group="Infra", type="dns", host="example.com")
    loop = asyncio.get_running_loop()

    async def resolved(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(loop, "getaddrinfo", resolved)
    result = await check_dns(monitor, 1)
    assert result.success and result.metadata["address_count"] == 1

    async def missing(*args, **kwargs):
        raise socket.gaierror(socket.EAI_NONAME, "missing")

    monkeypatch.setattr(loop, "getaddrinfo", missing)
    assert (await check_dns(monitor, 1)).error_code == "dns_not_found"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("days", "success", "status"), [(80, True, "up"), (20, True, "degraded"), (3, False, "down")]
)
async def test_tls_thresholds(
    monkeypatch: pytest.MonkeyPatch, days: int, success: bool, status: str
) -> None:
    from netpulse.checks import tls as tls_module

    def handshake(*args, **kwargs):
        return {
            "issuer": "CA",
            "subject": "example.com",
            "valid_from": "2026-01-01T00:00:00Z",
            "expires_at": "2026-12-01T00:00:00Z",
            "days_remaining": days,
        }

    monkeypatch.setattr(tls_module, "_handshake", handshake)
    monitor = TlsMonitor(
        id="tls_check",
        name="TLS",
        group="Security",
        type="tls",
        host="example.com",
        warning_days=30,
        critical_days=7,
    )
    result = await check_tls(monitor, 1)
    assert result.success is success and result.status == status


@pytest.mark.asyncio
async def test_tls_invalid_certificate(monkeypatch: pytest.MonkeyPatch) -> None:
    from netpulse.checks import tls as tls_module

    def invalid(*args, **kwargs):
        raise ssl.SSLCertVerificationError("hostname mismatch")

    monkeypatch.setattr(tls_module, "_handshake", invalid)
    monitor = TlsMonitor(
        id="tls_check", name="TLS", group="Security", type="tls", host="example.com"
    )
    assert (await check_tls(monitor, 1)).error_code == "tls_invalid"
