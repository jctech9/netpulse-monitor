"""TLS certificate checks with hostname and chain validation."""

from __future__ import annotations

import asyncio
import socket
import ssl
from datetime import UTC, datetime
from typing import Any

from ..models import CheckResult, TlsMonitor
from .base import Timer, result


def _name(parts: tuple[tuple[tuple[str, str], ...], ...]) -> str:
    return ", ".join(f"{key}={value}" for rdn in parts for pair in rdn for key, value in [pair])


def _handshake(host: str, port: int, timeout: float) -> dict[str, Any]:
    context = ssl.create_default_context()
    with (
        socket.create_connection((host, port), timeout=timeout) as raw_socket,
        context.wrap_socket(raw_socket, server_hostname=host) as tls_socket,
    ):
        certificate = tls_socket.getpeercert()
    if not certificate or "notAfter" not in certificate:
        raise ssl.SSLError("certificado remoto sem validade")
    expires_at = datetime.fromtimestamp(ssl.cert_time_to_seconds(certificate["notAfter"]), UTC)
    valid_from = datetime.fromtimestamp(ssl.cert_time_to_seconds(certificate["notBefore"]), UTC)
    days_remaining = (expires_at - datetime.now(UTC)).total_seconds() / 86400
    return {
        "issuer": _name(certificate.get("issuer", ())),
        "subject": _name(certificate.get("subject", ())),
        "valid_from": valid_from.isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "days_remaining": round(days_remaining, 1),
    }


async def check_tls(monitor: TlsMonitor, timeout: float) -> CheckResult:
    timer = Timer()
    try:
        metadata = await asyncio.wait_for(
            asyncio.to_thread(_handshake, monitor.host, monitor.port, timeout), timeout=timeout + 1
        )
        days = metadata["days_remaining"]
        if days <= monitor.critical_days:
            return result(
                monitor.id,
                False,
                f"Certificado expira em {days:.1f} dias",
                timer=timer,
                error_code="certificate_critical",
                metadata=metadata,
            )
        if days <= monitor.warning_days:
            return result(
                monitor.id,
                True,
                f"Certificado expira em {days:.1f} dias",
                timer=timer,
                status="degraded",
                error_code="certificate_warning",
                metadata=metadata,
            )
        return result(
            monitor.id,
            True,
            f"Certificado válido por {days:.1f} dias",
            timer=timer,
            metadata=metadata,
        )
    except TimeoutError:
        return result(monitor.id, False, "Tempo limite excedido", timer=timer, error_code="timeout")
    except (ssl.SSLError, ssl.CertificateError, OSError) as exc:
        return result(monitor.id, False, str(exc), timer=timer, error_code="tls_invalid")
