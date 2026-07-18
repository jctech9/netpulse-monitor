"""Deterministic, safe and visually rich development data."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

from .models import AppConfig
from .state import empty_state, isoformat


def demo_config() -> AppConfig:
    return AppConfig.model_validate(
        {
            "schema_version": 1,
            "settings": {"timezone": "America/Sao_Paulo", "notifications_enabled": False},
            "monitors": [
                {
                    "id": "portal_publico",
                    "name": "Portal público",
                    "group": "Web",
                    "type": "http",
                    "url": "https://example.com",
                    "description": "Página institucional de demonstração.",
                },
                {
                    "id": "api_catalogo",
                    "name": "API de catálogo",
                    "group": "APIs",
                    "type": "json",
                    "url": "https://api.example.com/catalog",
                    "json_path": "status",
                    "assertion": "equals",
                    "expected_value": "ok",
                    "description": "Endpoint JSON público de demonstração.",
                },
                {
                    "id": "conteudo_docs",
                    "name": "Central de documentação",
                    "group": "Web",
                    "type": "keyword",
                    "url": "https://docs.example.com",
                    "keyword": "Documentação",
                    "description": "Validação de conteúdo público.",
                },
                {
                    "id": "dns_edge",
                    "name": "DNS da borda",
                    "group": "Infraestrutura",
                    "type": "dns",
                    "host": "example.com",
                    "description": "Resolução DNS pública.",
                },
                {
                    "id": "gateway_https",
                    "name": "Gateway HTTPS",
                    "group": "Infraestrutura",
                    "type": "tcp",
                    "host": "example.com",
                    "port": 443,
                    "description": "Conectividade TCP do gateway.",
                },
                {
                    "id": "certificado_web",
                    "name": "Certificado web",
                    "group": "Segurança",
                    "type": "tls",
                    "host": "example.com",
                    "port": 443,
                    "description": "Certificado próximo da janela de atenção.",
                },
            ],
        }
    )


def build_demo_state(reference: datetime | None = None) -> tuple[dict[str, Any], AppConfig]:
    now = (reference or datetime.now(UTC)).replace(second=0, microsecond=0)
    config = demo_config()
    state = empty_state()
    state["updated_at"] = isoformat(now)
    final_statuses = {
        "portal_publico": "up",
        "api_catalogo": "degraded",
        "conteudo_docs": "up",
        "dns_edge": "down",
        "gateway_https": "maintenance",
        "certificado_web": "degraded",
    }
    base_latencies = {
        "portal_publico": 118,
        "api_catalogo": 265,
        "conteudo_docs": 83,
        "dns_edge": 41,
        "gateway_https": 72,
        "certificado_web": 156,
    }
    for monitor_index, monitor in enumerate(config.monitors):
        samples = []
        for point in range(144):
            timestamp = now - timedelta(minutes=(143 - point) * 10)
            wave = math.sin((point + monitor_index * 7) / 9) * 22
            latency = round(max(12, base_latencies[monitor.id] + wave + (point % 5) * 3), 2)
            status = "up"
            if monitor.id == "api_catalogo" and point in {89, 90, 142, 143}:
                status = "degraded"
                latency += 390
            elif monitor.id == "dns_edge" and point >= 132:
                status = "down"
                latency = None
            elif monitor.id == "gateway_https" and point >= 126:
                status = "maintenance"
            elif monitor.id == "certificado_web" and point >= 120:
                status = "degraded"
            samples.append(
                {"timestamp": isoformat(timestamp), "status": status, "response_ms": latency}
            )
        current_status = final_statuses[monitor.id]
        metadata: dict[str, Any] = {}
        detail = "Verificação concluída"
        if monitor.id == "certificado_web":
            metadata = {
                "issuer": "CN=Example Trust Services",
                "subject": "CN=example.com",
                "valid_from": isoformat(now - timedelta(days=330)),
                "expires_at": isoformat(now + timedelta(days=19)),
                "days_remaining": 19,
            }
            detail = "Certificado expira em 19 dias"
        elif current_status == "down":
            detail = "Falha na resolução DNS"
        elif current_status == "maintenance":
            detail = "Janela de manutenção programada"
        elif current_status == "degraded":
            detail = "Resposta acima do padrão esperado"
        state["monitors"][monitor.id] = {
            "status": current_status,
            "consecutive_failures": 2 if current_status == "down" else 0,
            "consecutive_successes": 0,
            "config_fingerprint": "demo",
            "last_result": {
                "monitor_id": monitor.id,
                "success": current_status not in {"down"},
                "status": current_status,
                "checked_at": isoformat(now),
                "response_ms": samples[-1]["response_ms"],
                "detail": detail,
                "error_code": "dns_not_found" if current_status == "down" else None,
                "metadata": metadata,
            },
        }
        state["history"][monitor.id] = {"raw": samples, "hourly": []}
    resolved_start = now - timedelta(hours=16, minutes=40)
    resolved_end = resolved_start + timedelta(minutes=34)
    open_start = now - timedelta(minutes=110)
    state["incidents"] = [
        {
            "id": "inc_demo_resolved",
            "monitor_id": "portal_publico",
            "started_at": isoformat(resolved_start),
            "ended_at": isoformat(resolved_end),
            "cause": "Tempo limite excedido",
            "duration_seconds": 2040,
            "status": "resolved",
            "message": "Oscilação resolvida; serviço normalizado.",
        },
        {
            "id": "inc_demo_open",
            "monitor_id": "dns_edge",
            "started_at": isoformat(open_start),
            "ended_at": None,
            "cause": "Falha na resolução DNS",
            "duration_seconds": None,
            "status": "open",
            "message": "Investigando indisponibilidade no resolvedor público.",
        },
    ]
    return state, config
