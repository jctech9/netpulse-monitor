from datetime import UTC, datetime, timedelta

from netpulse.state import empty_state, update_state


def test_first_success_is_up_without_alert(base_config, result_factory) -> None:
    state = update_state(empty_state(), base_config, [result_factory(True)])
    assert state["monitors"]["example_web"]["status"] == "up"
    assert state["pending_events"] == []


def test_failure_threshold_no_duplicates_and_recovery(base_config, result_factory) -> None:
    state = empty_state()
    start = datetime(2026, 7, 18, 15, 0, tzinfo=UTC)
    update_state(state, base_config, [result_factory(True, start)])
    update_state(state, base_config, [result_factory(False, start + timedelta(minutes=10))])
    assert state["monitors"]["example_web"]["status"] == "degraded"
    assert state["incidents"] == []
    update_state(state, base_config, [result_factory(False, start + timedelta(minutes=20))])
    assert state["monitors"]["example_web"]["status"] == "down"
    assert len(state["incidents"]) == 1
    assert len(state["pending_events"]) == 1
    update_state(state, base_config, [result_factory(False, start + timedelta(minutes=30))])
    assert len(state["pending_events"]) == 1
    update_state(state, base_config, [result_factory(True, start + timedelta(minutes=40))])
    assert state["monitors"]["example_web"]["status"] == "up"
    assert state["incidents"][0]["duration_seconds"] == 1200
    assert len(state["pending_events"]) == 2
    assert state["pending_events"][1]["kind"] == "recovery"


def test_maintenance_never_opens_incident(base_config, result_factory) -> None:
    base_config.monitors[0].maintenance = True
    state = update_state(empty_state(), base_config, [result_factory(False)])
    assert state["monitors"]["example_web"]["status"] == "maintenance"
    assert not state["incidents"]


def test_changed_configuration_does_not_open_false_incident(base_config, result_factory) -> None:
    state = update_state(empty_state(), base_config, [result_factory(True)])
    base_config.monitors[0].url = "https://www.example.com"
    state["monitors"]["example_web"]["consecutive_failures"] = 1
    update_state(state, base_config, [result_factory(False)])
    assert state["monitors"]["example_web"]["status"] == "degraded"
    assert not state["incidents"]
