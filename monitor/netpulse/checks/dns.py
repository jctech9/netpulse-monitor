"""DNS checks using the runner resolver."""

import asyncio
import socket

from ..models import CheckResult, DnsMonitor
from .base import Timer, result


async def check_dns(monitor: DnsMonitor, timeout: float) -> CheckResult:
    timer = Timer()
    loop = asyncio.get_running_loop()
    try:
        records = await asyncio.wait_for(
            loop.getaddrinfo(monitor.host, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM),
            timeout=timeout,
        )
        addresses = sorted({record[4][0] for record in records})
        preview = addresses[:3]
        return result(
            monitor.id,
            bool(addresses),
            f"{len(addresses)} endereço(s) resolvido(s)",
            timer=timer,
            error_code=None if addresses else "no_records",
            metadata={"address_count": len(addresses), "addresses": preview},
        )
    except TimeoutError:
        return result(monitor.id, False, "Tempo limite excedido", timer=timer, error_code="timeout")
    except socket.gaierror as exc:
        temporary = exc.errno == getattr(socket, "EAI_AGAIN", -3)
        code = "dns_temporary_failure" if temporary else "dns_not_found"
        return result(monitor.id, False, "Falha na resolução DNS", timer=timer, error_code=code)
