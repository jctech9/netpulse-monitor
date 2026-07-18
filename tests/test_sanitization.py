from netpulse.sanitization import sanitize_error, sanitize_metadata, sanitize_url


def test_sanitizes_credentials_and_query() -> None:
    assert (
        sanitize_url("https://user:pass@example.com/private?token=secret")
        == "https://example.com/private"
    )
    assert "user" not in sanitize_error("failed https://user:pass@example.com")


def test_sanitizes_paths_tokens_and_metadata() -> None:
    token = "123456789:" + ("a" * 29)
    error = sanitize_error(f"{token} C:\\Users\\person\\secret.txt")
    assert token not in error and "person" not in error
    public = sanitize_metadata(
        {"Authorization": "secret", "ok": "visible", "nested": {"chat_id": "42"}}
    )
    assert public == {"ok": "visible", "nested": {}}
