import httpx
import pytest
from netpulse.notifications import deliver_pending, send_text, split_message
from netpulse.state import empty_state


def test_split_message_near_limit() -> None:
    chunks = split_message("line\n" * 2000, limit=100)
    assert len(chunks) > 2
    assert all(len(chunk) <= 100 for chunk in chunks)


@pytest.mark.asyncio
async def test_missing_token_leaves_pending(monkeypatch, base_config) -> None:
    base_config.settings.notifications_enabled = True
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    state = empty_state()
    state["pending_events"] = [{"id": "event", "kind": "down", "monitor_id": "example_web"}]
    errors = await deliver_pending(state, base_config)
    assert errors and len(state["pending_events"]) == 1


@pytest.mark.asyncio
async def test_failed_delivery_never_exposes_token(monkeypatch) -> None:
    token = "123456789:" + ("a" * 29)

    async def failing_post(self, url, **kwargs):
        request = httpx.Request("POST", url)
        raise httpx.ConnectError(f"failed {url}", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "post", failing_post)
    success, next_chunk, error = await send_text("hello", token, "42")
    assert not success and next_chunk == 0
    assert token not in (error or "")


@pytest.mark.asyncio
async def test_queue_marks_success_once(monkeypatch, base_config) -> None:
    from netpulse import notifications

    base_config.settings.notifications_enabled = True
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")

    async def success(*args, **kwargs):
        return True, 1, None

    monkeypatch.setattr(notifications, "send_text", success)
    state = empty_state()
    state["pending_events"] = [
        {
            "id": "event",
            "kind": "down",
            "monitor_id": "example_web",
            "created_at": "2026-07-18T15:00:00Z",
            "detail": "Timeout",
            "consecutive_failures": 2,
        }
    ]
    assert await deliver_pending(state, base_config) == []
    assert not state["pending_events"] and state["delivered_event_ids"] == ["event"]
