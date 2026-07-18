from netpulse.demo import build_demo_state
from netpulse.public_data import build_public_data


def test_demo_contract_is_complete_and_sanitized() -> None:
    state, config = build_demo_state()
    status, history, incidents = build_public_data(state, config, demo=True)
    assert status["schema_version"] == 1 and status["demo"] is True
    assert len(status["monitors"]) == 6
    assert {item["status"] for item in status["monitors"]} >= {
        "up",
        "degraded",
        "down",
        "maintenance",
    }
    assert len(incidents["incidents"]) == 2
    assert all(len(bucket["raw"]) == 144 for bucket in history["monitors"].values())
    assert "?" not in next(item["target"] for item in status["monitors"] if item["type"] == "json")
