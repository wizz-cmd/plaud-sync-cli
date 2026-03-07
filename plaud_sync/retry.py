"""Retry with exponential backoff for transient API errors."""

from __future__ import annotations

import re
import time
import logging
from dataclasses import dataclass, field
from typing import TypeVar, Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")

_TOKEN_RE = re.compile(r"Bearer\s+[A-Za-z0-9._~-]+", re.IGNORECASE)


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_ms: int = 300
    max_delay_ms: int = 2000


class PlaudApiError(Exception):
    """Error from the Plaud API with category and status code."""

    def __init__(self, message: str, category: str = "network", status: int | None = None):
        super().__init__(message)
        self.category = category
        self.status = status


def classify_status(status: int) -> str:
    """Map HTTP status code to error category."""
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "rate_limit"
    if status >= 500:
        return "server"
    return "network"


def is_transient(category: str) -> bool:
    """Return True if the error category is transient and worth retrying."""
    return category in ("network", "rate_limit", "server")


def redact_tokens(message: str) -> str:
    """Replace Bearer tokens in a message with [REDACTED]."""
    return _TOKEN_RE.sub("Bearer [REDACTED]", message)


def retry_with_backoff(
    operation: str,
    fn: Callable[[], T],
    policy: RetryPolicy | None = None,
) -> T:
    """Execute fn with retry on transient errors.

    Args:
        operation: Name of the operation (for logging).
        fn: Callable to execute.
        policy: Retry policy (defaults to RetryPolicy()).

    Returns:
        The result of fn().

    Raises:
        PlaudApiError: On non-transient errors or after exhausting retries.
    """
    if policy is None:
        policy = RetryPolicy()

    last_error: Exception | None = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn()
        except PlaudApiError as e:
            last_error = e
            is_final = attempt >= policy.max_attempts
            transient = is_transient(e.category)

            if not transient or is_final:
                raise

            delay_ms = min(
                policy.base_delay_ms * (2 ** (attempt - 1)),
                policy.max_delay_ms,
            )

            logger.debug(
                "Retry %s attempt=%d/%d delay=%dms category=%s message=%s",
                operation,
                attempt,
                policy.max_attempts,
                delay_ms,
                e.category,
                redact_tokens(str(e)),
            )

            time.sleep(delay_ms / 1000.0)

    # Should not reach here, but just in case
    raise last_error  # type: ignore[misc]
