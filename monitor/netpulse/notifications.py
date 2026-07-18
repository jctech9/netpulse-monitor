"""Telegram delivery with a durable event queue and no POST retries."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .models import AppConfig
from .sanitization import sanitize_error

MAX_TELEGRAM_TEXT = 3900


def split_message(text: str, limit: int = MAX_TELEGRAM_TEXT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    return chunks


def local_time(value: str, timezone: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(ZoneInfo(timezone)).strftime("%d/%m/%Y às %H:%M")


def duration_text(seconds: int | None) -> str:
    if seconds is None:
        return "não calculada"
    minutes = max(0, round(seconds / 60))
    if minutes < 60:
        return f"{minutes}min"
    hours, rest = divmod(minutes, 60)
    return f"{hours}h {rest}min"


def format_event(event: dict[str, Any], config: AppConfig) -> str:
    monitor = next(item for item in config.monitors if item.id == event["monitor_id"])
    if event["kind"] == "down":
        return (
            "🔴 Serviço indisponível\n"
            f"Nome: {monitor.name}\n"
            f"Tipo: {monitor.type.upper()}\n"
            f"Motivo: {sanitize_error(event.get('detail', 'Falha confirmada'))}\n"
            f"Falhas consecutivas: {event.get('consecutive_failures', 0)}\n"
            f"Detectado: {local_time(event['created_at'], config.settings.timezone)}"
        )
    latency = event.get("response_ms")
    response = sanitize_error(event.get("detail", "Serviço saudável"))
    if latency is not None:
        response += f" em {latency:.0f} ms"
    return (
        "🟢 Serviço normalizado\n"
        f"Nome: {monitor.name}\n"
        f"Resposta: {response}\n"
        f"Indisponibilidade: {duration_text(event.get('duration_seconds'))}\n"
        f"Normalizado: {local_time(event['created_at'], config.settings.timezone)}"
    )


def format_summary(state: dict[str, Any], config: AppConfig) -> str:
    counts = {status: 0 for status in ("up", "degraded", "down", "maintenance", "unknown")}
    for item in state.get("monitors", {}).values():
        counts[item.get("status", "unknown")] += 1
    return (
        "📡 Resumo manual do NetPulse\n"
        f"Online: {counts['up']}\n"
        f"Instável: {counts['degraded']}\n"
        f"Offline: {counts['down']}\n"
        f"Manutenção: {counts['maintenance']}\n"
        f"Gerado: {local_time(state['updated_at'], config.settings.timezone)}"
    )


async def send_text(
    text: str, token: str, chat_id: str, start_chunk: int = 0
) -> tuple[bool, int, str | None]:
    chunks = split_message(text)
    # No retries: each POST is attempted exactly once.
    async with httpx.AsyncClient(timeout=httpx.Timeout(10), verify=True) as client:
        for index in range(start_chunk, len(chunks)):
            try:
                response = await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": chunks[index],
                        "disable_web_page_preview": True,
                    },
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                return False, index, sanitize_error(str(exc).replace(token, "[segredo removido]"))
    return True, len(chunks), None


async def deliver_pending(
    state: dict[str, Any], config: AppConfig, *, summary: bool = False
) -> list[str]:
    if not config.settings.notifications_enabled:
        return []
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return (
            ["Telegram não configurado; eventos permaneceram na fila."]
            if state["pending_events"]
            else []
        )
    errors: list[str] = []
    remaining: list[dict[str, Any]] = []
    for event in state["pending_events"]:
        try:
            message = format_event(event, config)
        except (KeyError, StopIteration) as exc:
            errors.append(
                f"Evento {event.get('id', 'desconhecido')} inválido: {sanitize_error(exc)}"
            )
            remaining.append(event)
            continue
        success, next_chunk, error = await send_text(
            message, token, chat_id, int(event.get("next_chunk", 0))
        )
        if success:
            state["delivered_event_ids"].append(event["id"])
        else:
            event["next_chunk"] = next_chunk
            event["last_error"] = error
            remaining.append(event)
            errors.append(error or "Falha desconhecida no Telegram")
    state["pending_events"] = remaining
    if summary:
        success, _, error = await send_text(format_summary(state, config), token, chat_id)
        if not success:
            errors.append(error or "Falha no envio do resumo")
    return errors
