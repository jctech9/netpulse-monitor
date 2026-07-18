"""Raw history retention, hourly aggregation and availability."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from statistics import mean
from typing import Any

EXCLUDED_STATUSES = {"unknown", "maintenance"}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def dominant_status(samples: list[dict[str, Any]]) -> str:
    if not samples:
        return "unknown"
    priority = {"down": 4, "degraded": 3, "maintenance": 2, "up": 1, "unknown": 0}
    counts = Counter(str(sample.get("status", "unknown")) for sample in samples)
    return max(counts, key=lambda status: (counts[status], priority.get(status, 0)))


def aggregate_hour(samples: list[dict[str, Any]], hour: datetime) -> dict[str, Any]:
    latencies = [
        float(item["response_ms"]) for item in samples if item.get("response_ms") is not None
    ]
    return {
        "timestamp": hour.isoformat().replace("+00:00", "Z"),
        "status": dominant_status(samples),
        "avg_ms": round(mean(latencies), 2) if latencies else None,
        "min_ms": round(min(latencies), 2) if latencies else None,
        "max_ms": round(max(latencies), 2) if latencies else None,
        "sample_count": len(samples),
        "status_counts": dict(Counter(str(item.get("status", "unknown")) for item in samples)),
    }


def update_history(
    history: dict[str, Any],
    monitor_id: str,
    sample: dict[str, Any],
    *,
    now: datetime,
    raw_hours: int,
    hourly_days: int,
) -> None:
    bucket = history.setdefault(monitor_id, {"raw": [], "hourly": []})
    bucket.setdefault("raw", []).append(sample)
    bucket["raw"].sort(key=lambda item: item["timestamp"])
    raw_cutoff = now - timedelta(hours=raw_hours)
    old = [item for item in bucket["raw"] if parse_time(item["timestamp"]) < raw_cutoff]
    bucket["raw"] = [item for item in bucket["raw"] if parse_time(item["timestamp"]) >= raw_cutoff]

    hourly_by_key = {item["timestamp"]: item for item in bucket.setdefault("hourly", [])}
    grouped: dict[datetime, list[dict[str, Any]]] = {}
    for item in old:
        timestamp = parse_time(item["timestamp"]).replace(minute=0, second=0, microsecond=0)
        grouped.setdefault(timestamp, []).append(item)
    for hour, items in grouped.items():
        key = hour.isoformat().replace("+00:00", "Z")
        existing = hourly_by_key.get(key)
        if existing:
            # Preserve totals when an hour is aggregated in more than one execution.
            synthetic = []
            for status, count in existing.get("status_counts", {}).items():
                synthetic.extend(
                    {"status": status, "response_ms": existing.get("avg_ms")} for _ in range(count)
                )
            items = synthetic + items
        hourly_by_key[key] = aggregate_hour(items, hour)

    hourly_cutoff = now - timedelta(days=hourly_days)
    bucket["hourly"] = sorted(
        (item for item in hourly_by_key.values() if parse_time(item["timestamp"]) >= hourly_cutoff),
        key=lambda item: item["timestamp"],
    )


def availability(samples: list[dict[str, Any]]) -> float | None:
    eligible = [item for item in samples if item.get("status") not in EXCLUDED_STATUSES]
    if not eligible:
        return None
    healthy = sum(item.get("status") == "up" for item in eligible)
    return round(healthy / len(eligible) * 100, 3)


def period_samples(bucket: dict[str, Any], now: datetime, hours: int) -> list[dict[str, Any]]:
    cutoff = now - timedelta(hours=hours)
    return [item for item in bucket.get("raw", []) if parse_time(item["timestamp"]) >= cutoff]


def availability_30d(bucket: dict[str, Any]) -> float | None:
    counts: Counter[str] = Counter()
    for item in bucket.get("hourly", []):
        counts.update(item.get("status_counts", {}))
    counts.update(str(item.get("status", "unknown")) for item in bucket.get("raw", []))
    denominator = sum(count for status, count in counts.items() if status not in EXCLUDED_STATUSES)
    return round(counts["up"] / denominator * 100, 3) if denominator else None
