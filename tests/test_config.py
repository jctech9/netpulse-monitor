from pathlib import Path

import pytest
from netpulse.config import ConfigError, load_config
from netpulse.models import AppConfig


def test_loads_public_configuration() -> None:
    config = load_config(Path("config/monitors.yml"))
    assert len(config.monitors) == 6
    assert {monitor.type for monitor in config.monitors} == {
        "http",
        "json",
        "keyword",
        "dns",
        "tcp",
        "tls",
    }


def test_rejects_invalid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yml"
    path.write_text("monitors: [\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="YAML inválido"):
        load_config(path)


def test_rejects_duplicate_ids() -> None:
    monitor = {
        "id": "same_id",
        "name": "Same",
        "group": "Web",
        "type": "http",
        "url": "https://example.com",
    }
    with pytest.raises(ValueError, match="duplicados"):
        AppConfig.model_validate({"schema_version": 1, "monitors": [monitor, monitor]})


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"url": "example.com"}, "URL absoluta"),
        ({"method": "POST"}, "GET.*HEAD|Input should be"),
        ({"id": "Unsafe ID"}, "caracteres"),
    ],
)
def test_rejects_invalid_http_fields(changes: dict, message: str) -> None:
    monitor = {
        "id": "valid_id",
        "name": "Example",
        "group": "Web",
        "type": "http",
        "url": "https://example.com",
        **changes,
    }
    with pytest.raises(ValueError, match=message):
        AppConfig.model_validate({"schema_version": 1, "monitors": [monitor]})


@pytest.mark.parametrize("port", [0, 65536])
def test_rejects_invalid_port(port: int) -> None:
    with pytest.raises(ValueError):
        AppConfig.model_validate(
            {
                "schema_version": 1,
                "monitors": [
                    {
                        "id": "tcp_port",
                        "name": "TCP",
                        "group": "Infra",
                        "type": "tcp",
                        "host": "example.com",
                        "port": port,
                    }
                ],
            }
        )


def test_rejects_unknown_monitor_type() -> None:
    with pytest.raises(ValueError, match=r"tag|type"):
        AppConfig.model_validate(
            {
                "schema_version": 1,
                "monitors": [{"id": "bad_type", "name": "Bad", "group": "Bad", "type": "smtp"}],
            }
        )
