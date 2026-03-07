"""Tests for plaud_sync.config module."""

import json
import os
import pytest
from pathlib import Path

from plaud_sync.config import (
    load_config,
    load_token,
    load_state,
    save_state,
    Config,
    DEFAULT_API_DOMAIN,
    DEFAULT_SYNC_FOLDER,
    DEFAULT_FILENAME_PATTERN,
)


class TestLoadConfig:
    def test_defaults_when_no_file(self, tmp_path):
        config = load_config(str(tmp_path / "nonexistent.json"))
        assert config.api_domain == DEFAULT_API_DOMAIN
        assert config.sync_folder == DEFAULT_SYNC_FOLDER
        assert config.update_existing is True
        assert config.filename_pattern == DEFAULT_FILENAME_PATTERN

    def test_loads_from_file(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "apiDomain": "https://custom.api.com",
            "syncFolder": "MyNotes",
            "updateExisting": False,
            "filenamePattern": "{date}-{title}",
        }))
        config = load_config(str(config_file))
        assert config.api_domain == "https://custom.api.com"
        assert config.sync_folder == "MyNotes"
        assert config.update_existing is False
        assert config.filename_pattern == "{date}-{title}"

    def test_partial_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"syncFolder": "Notes"}))
        config = load_config(str(config_file))
        assert config.sync_folder == "Notes"
        assert config.api_domain == DEFAULT_API_DOMAIN

    def test_invalid_json(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("not json")
        config = load_config(str(config_file))
        assert config.api_domain == DEFAULT_API_DOMAIN


class TestLoadToken:
    def test_loads_token(self, tmp_path):
        token_file = tmp_path / "token.txt"
        token_file.write_text("my-secret-token\n")
        assert load_token(str(token_file)) == "my-secret-token"

    def test_missing_file_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            load_token(str(tmp_path / "missing.txt"))

    def test_empty_file_exits(self, tmp_path):
        token_file = tmp_path / "token.txt"
        token_file.write_text("")
        with pytest.raises(SystemExit):
            load_token(str(token_file))


class TestState:
    def test_load_missing_state(self, tmp_path):
        state = load_state(tmp_path / "state.json")
        assert state == {"lastSyncAtMs": 0}

    def test_save_and_load_state(self, tmp_path):
        state_path = tmp_path / "state.json"
        save_state(state_path, {"lastSyncAtMs": 12345})
        state = load_state(state_path)
        assert state["lastSyncAtMs"] == 12345

    def test_invalid_state_file(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text("not json")
        state = load_state(state_path)
        assert state == {"lastSyncAtMs": 0}
