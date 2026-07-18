"""Validated configuration and runtime contracts."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

MonitorStatus = Literal["unknown", "up", "degraded", "down", "maintenance"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Settings(StrictModel):
    timezone: str = "America/Sao_Paulo"
    default_timeout_seconds: float = Field(default=8, gt=0, le=60)
    default_failure_threshold: int = Field(default=2, ge=1, le=20)
    default_recovery_threshold: int = Field(default=1, ge=1, le=20)
    max_concurrency: int = Field(default=10, ge=1, le=50)
    raw_history_hours: int = Field(default=24, ge=1, le=168)
    hourly_history_days: int = Field(default=30, ge=1, le=365)
    incident_retention_days: int = Field(default=90, ge=1, le=730)
    notifications_enabled: bool = True


class MonitorBase(StrictModel):
    id: str
    name: str = Field(min_length=1, max_length=100)
    group: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=240)
    enabled: bool = True
    maintenance: bool = False
    notifications_enabled: bool = True
    timeout_seconds: float | None = Field(default=None, gt=0, le=60)
    failure_threshold: int | None = Field(default=None, ge=1, le=20)
    recovery_threshold: int | None = Field(default=None, ge=1, le=20)

    @field_validator("id")
    @classmethod
    def safe_id(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", value):
            raise ValueError("deve usar 2-64 caracteres: a-z, 0-9, _ ou -")
        return value

    @field_validator("name", "group", "description")
    @classmethod
    def no_control_chars(cls, value: str) -> str:
        if any(ord(char) < 32 and char not in "\t" for char in value):
            raise ValueError("não pode conter caracteres de controle")
        return value.strip()


class WebMonitor(MonitorBase):
    url: str
    method: Literal["GET", "HEAD"] = "GET"
    expected_status: list[int] = Field(default_factory=lambda: [200], min_length=1)
    follow_redirects: bool = True
    retries: int = Field(default=1, ge=0, le=2)

    @field_validator("url")
    @classmethod
    def public_http_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("deve ser uma URL absoluta com esquema http ou https")
        if parsed.username or parsed.password:
            raise ValueError("não pode conter credenciais")
        return value

    @field_validator("expected_status")
    @classmethod
    def valid_statuses(cls, value: list[int]) -> list[int]:
        if any(status < 100 or status > 599 for status in value):
            raise ValueError("deve conter códigos HTTP entre 100 e 599")
        return sorted(set(value))


class HttpMonitor(WebMonitor):
    type: Literal["http"]


class KeywordMonitor(WebMonitor):
    type: Literal["keyword"]
    method: Literal["GET"] = "GET"
    keyword: str = Field(min_length=1, max_length=500)
    expectation: Literal["present", "absent"] = "present"
    case_sensitive: bool = False


class JsonMonitor(WebMonitor):
    type: Literal["json"]
    method: Literal["GET"] = "GET"
    json_path: str = Field(min_length=1, max_length=200)
    assertion: Literal["exists", "equals", "not_equals", "greater_than", "less_than"]
    expected_value: Any = None

    @model_validator(mode="after")
    def assertion_has_value(self) -> JsonMonitor:
        if self.assertion != "exists" and self.expected_value is None:
            raise ValueError("expected_value é obrigatório para esta assertiva")
        return self


class HostMonitor(MonitorBase):
    host: str = Field(min_length=1, max_length=253)

    @field_validator("host")
    @classmethod
    def safe_host(cls, value: str) -> str:
        if "/" in value or "://" in value or "@" in value or any(c.isspace() for c in value):
            raise ValueError("deve ser um hostname sem esquema, caminho ou credenciais")
        return value.rstrip(".")


class TcpMonitor(HostMonitor):
    type: Literal["tcp"]
    port: int = Field(ge=1, le=65535)


class DnsMonitor(HostMonitor):
    type: Literal["dns"]


class TlsMonitor(HostMonitor):
    type: Literal["tls"]
    port: int = Field(default=443, ge=1, le=65535)
    warning_days: int = Field(default=30, ge=1, le=365)
    critical_days: int = Field(default=7, ge=0, le=90)

    @model_validator(mode="after")
    def thresholds_ordered(self) -> TlsMonitor:
        if self.critical_days >= self.warning_days:
            raise ValueError("critical_days deve ser menor que warning_days")
        return self


Monitor = Annotated[
    HttpMonitor | KeywordMonitor | JsonMonitor | TcpMonitor | DnsMonitor | TlsMonitor,
    Field(discriminator="type"),
]
MONITOR_ADAPTER = TypeAdapter(Monitor)


class AppConfig(StrictModel):
    schema_version: Literal[1]
    settings: Settings = Field(default_factory=Settings)
    monitors: list[Monitor] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self) -> AppConfig:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for monitor in self.monitors:
            if monitor.id in seen:
                duplicates.add(monitor.id)
            seen.add(monitor.id)
        if duplicates:
            raise ValueError(f"IDs de monitor duplicados: {', '.join(sorted(duplicates))}")
        return self


class CheckResult(StrictModel):
    monitor_id: str
    success: bool
    status: MonitorStatus
    checked_at: datetime
    response_ms: float | None = Field(default=None, ge=0)
    detail: str = Field(max_length=300)
    error_code: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("checked_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("checked_at deve possuir timezone")
        return value.astimezone(UTC)
