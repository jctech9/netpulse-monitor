"""Configuration loading with actionable validation errors."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import AppConfig


class ConfigError(ValueError):
    """Raised when configuration cannot be parsed or validated."""


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    try:
        content = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Não foi possível ler {config_path}: {exc}") from exc
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML inválido em {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"A raiz de {config_path} deve ser um objeto YAML")
    try:
        return AppConfig.model_validate(data)
    except ValidationError as exc:
        messages = []
        for error in exc.errors(include_url=False):
            location = ".".join(str(item) for item in error["loc"])
            messages.append(f"{location}: {error['msg']}")
        raise ConfigError("Configuração inválida:\n- " + "\n- ".join(messages)) from exc
