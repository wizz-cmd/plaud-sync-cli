"""Configuration loading for Plaud Sync CLI."""

from __future__ import annotations

import json
import os
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_API_DOMAIN = "https://api.plaud.ai"
DEFAULT_SYNC_FOLDER = "Plaud"
DEFAULT_FILENAME_PATTERN = "{date}-{title}"
DEFAULT_CONFIG_PATH = "~/.config/plaud-sync/config.json"
DEFAULT_TOKEN_PATH = "~/.secrets/plaud.txt"
STATE_FILENAME = ".plaud-sync-state.json"


@dataclass
class Config:
    """Configuration for the Plaud Sync CLI."""
    api_domain: str = DEFAULT_API_DOMAIN
    sync_folder: str = DEFAULT_SYNC_FOLDER
    update_existing: bool = True
    filename_pattern: str = DEFAULT_FILENAME_PATTERN


def load_config(config_path: str | None = None) -> Config:
    """Load configuration from a JSON file.

    Args:
        config_path: Path to config file. Defaults to ~/.config/plaud-sync/config.json.

    Returns:
        Config object with values from file merged with defaults.
    """
    path = Path(os.path.expanduser(config_path or DEFAULT_CONFIG_PATH))

    if not path.exists():
        logger.debug("No config file at %s, using defaults", path)
        return Config()

    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load config from %s: %s", path, e)
        return Config()

    if not isinstance(data, dict):
        return Config()

    return Config(
        api_domain=_str_field(data, "apiDomain", DEFAULT_API_DOMAIN),
        sync_folder=_str_field(data, "syncFolder", DEFAULT_SYNC_FOLDER),
        update_existing=_bool_field(data, "updateExisting", True),
        filename_pattern=_str_field(data, "filenamePattern", DEFAULT_FILENAME_PATTERN),
    )


def load_token(token_file: str | None = None) -> str:
    """Load API token from a file.

    Args:
        token_file: Path to token file. Defaults to ~/.secrets/plaud.txt.

    Returns:
        The token string.

    Raises:
        SystemExit: If the token file cannot be read.
    """
    path = Path(os.path.expanduser(token_file or DEFAULT_TOKEN_PATH))

    if not path.exists():
        raise SystemExit(f"Token file not found: {path}")

    try:
        token = path.read_text().strip()
    except OSError as e:
        raise SystemExit(f"Failed to read token file: {e}")

    if not token:
        raise SystemExit(f"Token file is empty: {path}")

    return token


def load_state(state_path: Path) -> dict:
    """Load sync state from JSON file.

    Args:
        state_path: Path to state file.

    Returns:
        State dict with at least 'lastSyncAtMs' key.
    """
    if not state_path.exists():
        return {"lastSyncAtMs": 0}

    try:
        with open(state_path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load state from %s: %s", state_path, e)

    return {"lastSyncAtMs": 0}


def save_state(state_path: Path, state: dict) -> None:
    """Save sync state to JSON file.

    Args:
        state_path: Path to state file.
        state: State dict to save.
    """
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def _str_field(data: dict, key: str, default: str) -> str:
    val = data.get(key)
    if isinstance(val, str) and val.strip():
        return val.strip()
    return default


def _bool_field(data: dict, key: str, default: bool) -> bool:
    val = data.get(key)
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return default
