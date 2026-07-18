from datetime import UTC, datetime

import pytest
from netpulse.models import AppConfig, CheckResult


@pytest.fixture
def base_config() -> AppConfig:
    return AppConfig.model_validate(
        {
            "schema_version": 1,
            "settings": {
                "default_failure_threshold": 2,
                "default_recovery_threshold": 1,
                "notifications_enabled": False,
            },
            "monitors": [
                {
                    "id": "example_web",
                    "name": "Example Web",
                    "group": "Web",
                    "type": "http",
                    "url": "https://example.com",
                }
            ],
        }
    )


@pytest.fixture
def result_factory():
    def factory(success: bool, at: datetime | None = None, **changes) -> CheckResult:
        payload = {
            "monitor_id": "example_web",
            "success": success,
            "status": "up" if success else "down",
            "checked_at": at or datetime(2026, 7, 18, 15, 0, tzinfo=UTC),
            "response_ms": 125.5 if success else None,
            "detail": "HTTP 200" if success else "Tempo limite excedido",
            "error_code": None if success else "timeout",
            "metadata": {},
        }
        payload.update(changes)
        return CheckResult.model_validate(payload)

    return factory
