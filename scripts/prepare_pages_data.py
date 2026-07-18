"""Validate generated public JSON before the Vite build."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_document(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError(f"{path}: schema_version inválido")
    if not isinstance(data.get("generated_at"), str):
        raise ValueError(f"{path}: generated_at ausente")
    return data


def validate(directory: Path) -> None:
    status = load_document(directory / "status.json")
    history = load_document(directory / "history.json")
    incidents = load_document(directory / "incidents.json")
    if not isinstance(status.get("monitors"), list):
        raise ValueError("status.json: monitors deve ser uma lista")
    if not isinstance(history.get("monitors"), dict):
        raise ValueError("history.json: monitors deve ser um objeto")
    if not isinstance(incidents.get("incidents"), list):
        raise ValueError("incidents.json: incidents deve ser uma lista")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    validate(args.directory)
    print(f"JSONs públicos válidos em {args.directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
