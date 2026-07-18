"""TCP connect checks."""

import asyncio
from contextlib import suppress

from ..models import CheckResult, TcpMonitor
from .base import Timer, result


async def check_tcp(monitor: TcpMonitor, timeout: float) -> CheckResult:
    timer = Timer()
    writer: asyncio.StreamWriter | None = None
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(monitor.host, monitor.port), timeout=timeout
        )
        return result(
            monitor.id,
            True,
            f"Porta TCP {monitor.port} acessível",
            timer=timer,
            metadata={"port": monitor.port},
        )
    except TimeoutError:
        return result(monitor.id, False, "Tempo limite excedido", timer=timer, error_code="timeout")
    except OSError as exc:
        return result(monitor.id, False, str(exc), timer=timer, error_code="connection_failed")
    finally:
        if writer is not None:
            writer.close()
            with suppress(OSError):
                await writer.wait_closed()
