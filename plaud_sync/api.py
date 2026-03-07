"""Plaud API client for listing and fetching recording details."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from plaud_sync.retry import PlaudApiError, classify_status, retry_with_backoff, RetryPolicy

logger = logging.getLogger(__name__)


def normalize_domain(domain: str) -> str:
    """Strip trailing slashes from API domain."""
    return domain.rstrip("/")


def normalize_token(token: str) -> str:
    """Strip 'Bearer ' prefix and whitespace from token."""
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def _is_success_status(status: Any) -> bool:
    """Check if an API envelope status indicates success."""
    if isinstance(status, int):
        return status in (0, 200)
    if isinstance(status, str):
        return status.lower() in ("ok", "success", "0", "200")
    return False


def _extract_list_payload(envelope: dict) -> list[dict]:
    """Extract the file list from various envelope formats."""
    if "payload" in envelope and isinstance(envelope["payload"], list):
        return envelope["payload"]
    if "data_file_list" in envelope and isinstance(envelope["data_file_list"], list):
        return envelope["data_file_list"]
    if "data" in envelope and isinstance(envelope["data"], list):
        return envelope["data"]
    return []


def _extract_detail_payload(envelope: dict) -> dict:
    """Extract file detail from various envelope formats."""
    if "payload" in envelope and isinstance(envelope["payload"], dict):
        return envelope["payload"]
    if "data" in envelope and isinstance(envelope["data"], dict):
        return envelope["data"]
    return envelope


def _normalize_file_detail(detail: dict) -> dict:
    """Ensure both id and file_id are populated."""
    result = dict(detail)
    if "file_id" in result and "id" not in result:
        result["id"] = result["file_id"]
    elif "id" in result and "file_id" not in result:
        result["file_id"] = result["id"]
    return result


class PlaudApiClient:
    """Client for the Plaud.ai API."""

    def __init__(self, token: str, api_domain: str = "https://api.plaud.ai",
                 retry_policy: RetryPolicy | None = None):
        self.token = normalize_token(token)
        self.api_domain = normalize_domain(api_domain)
        self.retry_policy = retry_policy or RetryPolicy()

    def _request(self, path: str) -> dict:
        """Make an authenticated GET request to the API."""
        url = f"{self.api_domain}{path}"
        req = Request(url)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/json")

        try:
            with urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except HTTPError as e:
            category = classify_status(e.code)
            raise PlaudApiError(
                f"HTTP {e.code} from {url}",
                category=category,
                status=e.code,
            ) from e
        except (URLError, OSError) as e:
            raise PlaudApiError(
                f"Network error: {e}",
                category="network",
            ) from e
        except json.JSONDecodeError as e:
            raise PlaudApiError(
                f"Invalid JSON response from {url}",
                category="invalid_response",
            ) from e

    def list_files(self) -> list[dict]:
        """List all recordings from the API.

        Returns:
            List of file summary dicts with at least 'id' field.
        """
        def do_list() -> list[dict]:
            envelope = self._request("/file/simple/web")
            if isinstance(envelope, dict):
                status = envelope.get("status")
                if status is not None and not _is_success_status(status):
                    raise PlaudApiError(
                        f"API error: {envelope.get('msg', 'unknown')}",
                        category="server",
                    )
                return _extract_list_payload(envelope)
            return []

        return retry_with_backoff("list_files", do_list, self.retry_policy)

    def get_file_detail(self, file_id: str) -> dict:
        """Get detailed metadata for a specific recording.

        Args:
            file_id: The recording's file ID.

        Returns:
            Dict with recording detail fields.
        """
        def do_detail() -> dict:
            envelope = self._request(f"/file/detail/{file_id}")
            if isinstance(envelope, dict):
                status = envelope.get("status")
                if status is not None and not _is_success_status(status):
                    raise PlaudApiError(
                        f"API error for {file_id}: {envelope.get('msg', 'unknown')}",
                        category="server",
                    )
                detail = _extract_detail_payload(envelope)
                return _normalize_file_detail(detail)
            return {}

        return retry_with_backoff("get_file_detail", do_detail, self.retry_policy)

    def validate_token(self) -> bool:
        """Validate the API token by attempting to list files.

        Returns:
            True if the token is valid.

        Raises:
            PlaudApiError: If authentication fails.
        """
        self.list_files()
        return True
