"""Tests for plaud_sync.retry module."""

import pytest
from plaud_sync.retry import (
    PlaudApiError,
    classify_status,
    is_transient,
    redact_tokens,
    retry_with_backoff,
    RetryPolicy,
)


class TestClassifyStatus:
    def test_401_is_auth(self):
        assert classify_status(401) == "auth"

    def test_403_is_auth(self):
        assert classify_status(403) == "auth"

    def test_429_is_rate_limit(self):
        assert classify_status(429) == "rate_limit"

    def test_500_is_server(self):
        assert classify_status(500) == "server"

    def test_502_is_server(self):
        assert classify_status(502) == "server"

    def test_404_is_network(self):
        assert classify_status(404) == "network"


class TestIsTransient:
    def test_network_is_transient(self):
        assert is_transient("network") is True

    def test_rate_limit_is_transient(self):
        assert is_transient("rate_limit") is True

    def test_server_is_transient(self):
        assert is_transient("server") is True

    def test_auth_is_not_transient(self):
        assert is_transient("auth") is False

    def test_invalid_response_is_not_transient(self):
        assert is_transient("invalid_response") is False


class TestRedactTokens:
    def test_redacts_bearer_token(self):
        msg = "Authorization: Bearer abc123.xyz_456"
        assert "abc123" not in redact_tokens(msg)
        assert "[REDACTED]" in redact_tokens(msg)

    def test_no_token_unchanged(self):
        msg = "Some regular message"
        assert redact_tokens(msg) == msg


class TestRetryWithBackoff:
    def test_success_on_first_try(self):
        result = retry_with_backoff("test", lambda: 42)
        assert result == 42

    def test_retries_transient_error(self):
        calls = {"count": 0}

        def flaky():
            calls["count"] += 1
            if calls["count"] < 3:
                raise PlaudApiError("fail", category="network")
            return "ok"

        policy = RetryPolicy(max_attempts=3, base_delay_ms=1, max_delay_ms=10)
        result = retry_with_backoff("test", flaky, policy)
        assert result == "ok"
        assert calls["count"] == 3

    def test_does_not_retry_auth_error(self):
        def fail():
            raise PlaudApiError("auth fail", category="auth", status=401)

        with pytest.raises(PlaudApiError) as exc_info:
            retry_with_backoff("test", fail, RetryPolicy(base_delay_ms=1))
        assert exc_info.value.category == "auth"

    def test_raises_after_max_attempts(self):
        def always_fail():
            raise PlaudApiError("server error", category="server", status=500)

        policy = RetryPolicy(max_attempts=2, base_delay_ms=1, max_delay_ms=10)
        with pytest.raises(PlaudApiError):
            retry_with_backoff("test", always_fail, policy)
