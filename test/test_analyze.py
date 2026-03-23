"""Tests for plaud_sync.analyze module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plaud_sync.analyze import (
    AnalyzeError,
    NoLlmConfigError,
    build_prompt,
    list_templates,
    load_llm_config,
    load_template,
    parse_template,
    run_analysis,
)


class TestListTemplates:
    def test_lists_bundled(self):
        templates = list_templates()
        names = [t["name"] for t in templates]
        assert "default" in names
        assert "action-items" in names
        assert "executive-summary" in names

    def test_all_have_required_keys(self):
        for t in list_templates():
            assert "name" in t
            assert "path" in t
            assert "source" in t


class TestLoadTemplate:
    def test_loads_default(self):
        content = load_template("default")
        assert "{instructions}" in content
        assert "Zusammenfassung" in content

    def test_loads_with_md_extension(self):
        content = load_template("default.md")
        assert "{instructions}" in content

    def test_not_found(self):
        with pytest.raises(AnalyzeError, match="not found"):
            load_template("nonexistent-template-xyz")

    def test_user_overrides_bundled(self, tmp_path, monkeypatch):
        monkeypatch.setattr("plaud_sync.analyze._USER_DIR", tmp_path)
        (tmp_path / "default.md").write_text("USER VERSION")
        content = load_template("default")
        assert content == "USER VERSION"


class TestParseTemplate:
    def test_extracts_instructions(self):
        content = (
            "{instructions}\nDo something special.\n{/instructions}\n\n## Output\nHere."
        )
        system, output = parse_template(content)
        assert system == "Do something special."
        assert "## Output" in output
        assert "{instructions}" not in output

    def test_no_instructions(self):
        content = "## Just Output\nNo instructions here."
        system, output = parse_template(content)
        assert system == ""
        assert "Just Output" in output


class TestBuildPrompt:
    def test_basic(self):
        system, user = build_prompt("Hello world transcript")
        assert "transcript" in user.lower() or "TRANSCRIPT" in user
        assert "Hello world transcript" in user
        assert system  # Default template has instructions

    def test_with_extra_prompt(self):
        system, user = build_prompt("Test", extra_prompt="Focus on budget")
        assert "Focus on budget" in system

    def test_with_template(self):
        system, user = build_prompt("Test", template_name="action-items")
        assert "Action Items" in system or "Action Items" in user


class TestLoadLlmConfig:
    def test_no_config_file(self, tmp_path):
        with pytest.raises(NoLlmConfigError, match="No config file"):
            load_llm_config(str(tmp_path / "nonexistent.json"))

    def test_no_llm_section(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"apiDomain": "https://api.plaud.ai"}))
        with pytest.raises(NoLlmConfigError, match="No 'llm' section"):
            load_llm_config(str(cfg))

    def test_valid_config(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "llm": {"provider": "openai", "model": "gpt-4o", "apiKeyFile": "~/.secrets/openai.txt"}
        }))
        result = load_llm_config(str(cfg))
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o"


class TestRunAnalysis:
    def test_no_llm_configured(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text("{}")
        with pytest.raises(NoLlmConfigError):
            run_analysis("test transcript", config_path=str(cfg))

    @patch("plaud_sync.analyze._call_openai")
    def test_calls_openai(self, mock_call, tmp_path):
        cfg = tmp_path / "config.json"
        key_file = tmp_path / "key.txt"
        key_file.write_text("sk-test-key")
        cfg.write_text(json.dumps({
            "llm": {"provider": "openai", "model": "gpt-4o", "apiKeyFile": str(key_file)}
        }))

        mock_call.return_value = "Analysis result"
        result = run_analysis("Hello transcript", config_path=str(cfg))
        assert result == "Analysis result"
        mock_call.assert_called_once()
        args = mock_call.call_args
        assert args[0][0] == "sk-test-key"  # api_key
        assert args[0][1] == "gpt-4o"  # model

    def test_unsupported_provider(self, tmp_path):
        cfg = tmp_path / "config.json"
        key_file = tmp_path / "key.txt"
        key_file.write_text("test-key")
        cfg.write_text(json.dumps({
            "llm": {"provider": "unsupported", "apiKeyFile": str(key_file)}
        }))
        with pytest.raises(AnalyzeError, match="Unsupported"):
            run_analysis("test", config_path=str(cfg))
