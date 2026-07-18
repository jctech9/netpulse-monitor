"""Sanitization boundary for logs and public output."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

SENSITIVE_KEYS = re.compile(r"token|secret|password|authorization|cookie|chat.?id|api.?key", re.I)
WINDOWS_PATH = re.compile(r"[A-Za-z]:\\[^\s'\"]+")
POSIX_PATH = re.compile(r"(?<!:)\/(?:home|Users|tmp|var|opt)\/[^\s'\"]+")
TELEGRAM_TOKEN = re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_url(value: str, *, include_query: bool = False) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "destino inválido"
    if not parsed.scheme or not parsed.hostname:
        return CONTROL_CHARS.sub("", value)[:240]
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{parsed.hostname}{port}"
    query = parsed.query if include_query else ""
    return urlunsplit((parsed.scheme, netloc, parsed.path, query, ""))[:300]


def sanitize_error(value: object) -> str:
    text = str(value)
    text = TELEGRAM_TOKEN.sub("[segredo removido]", text)
    text = WINDOWS_PATH.sub("[caminho local removido]", text)
    text = POSIX_PATH.sub("[caminho local removido]", text)
    text = CONTROL_CHARS.sub("", text).replace("\r", " ").replace("\n", " ")
    # Remove credentials embedded in any URL-like token.
    text = re.sub(r"(https?://)[^/@\s]+@", r"\1", text)
    return text[:300]


def sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): sanitize_metadata(item)
            for key, item in value.items()
            if not SENSITIVE_KEYS.search(str(key))
        }
    if isinstance(value, list):
        return [sanitize_metadata(item) for item in value]
    if isinstance(value, str):
        return sanitize_error(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return sanitize_error(value)
