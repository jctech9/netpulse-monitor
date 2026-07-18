import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from netpulse.history import availability, update_history
from netpulse.state import atomic_write_json, empty_state, load_state


def sample(at: datetime, status: str, latency: float | None = 10) -> dict:
    return {
        "timestamp": at.isoformat().replace("+00:00", "Z"),
        "status": status,
        "response_ms": latency,
    }


def test_uptime_excludes_unknown_and_maintenance() -> None:
    samples = [
        sample(datetime.now(UTC), state) for state in ["up", "up", "down", "unknown", "maintenance"]
    ]
    assert availability(samples) == 66.667


def test_hourly_aggregation_and_retention() -> None:
    now = datetime(2026, 7, 18, 15, tzinfo=UTC)
    history: dict = {}
    for offset, status in [(26, "up"), (25, "down"), (1, "up")]:
        update_history(
            history,
            "service",
            sample(now - timedelta(hours=offset), status),
            now=now,
            raw_hours=24,
            hourly_days=30,
        )
    assert len(history["service"]["raw"]) == 1
    assert len(history["service"]["hourly"]) == 2
    assert history["service"]["hourly"][1]["status"] == "down"


def test_atomic_write_preserves_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    atomic_write_json(path, {"schema_version": 1, "value": "á"})
    assert json.loads(path.read_text(encoding="utf-8"))["value"] == "á"
    assert not list(tmp_path.glob("*.tmp"))


def test_invalid_state_recovers_empty(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{broken", encoding="utf-8")
    state, recovered = load_state(path)
    assert recovered and state == empty_state()
