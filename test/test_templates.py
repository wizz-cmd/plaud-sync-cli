"""Tests for bundled templates validity."""

from pathlib import Path

import pytest

from plaud_sync.analyze import list_templates, load_template, parse_template


BUNDLED_DIR = Path(__file__).parent.parent / "templates"

EXPECTED_TEMPLATES = ["default", "action-items", "executive-summary"]


class TestBundledTemplates:
    def test_all_expected_exist(self):
        names = [t["name"] for t in list_templates()]
        for expected in EXPECTED_TEMPLATES:
            assert expected in names, f"Missing bundled template: {expected}"

    @pytest.mark.parametrize("name", EXPECTED_TEMPLATES)
    def test_template_is_valid_markdown(self, name):
        content = load_template(name)
        assert len(content) > 10, f"Template {name} is too short"

    @pytest.mark.parametrize("name", EXPECTED_TEMPLATES)
    def test_template_has_instructions(self, name):
        content = load_template(name)
        assert "{instructions}" in content
        assert "{/instructions}" in content

    @pytest.mark.parametrize("name", EXPECTED_TEMPLATES)
    def test_template_parses(self, name):
        content = load_template(name)
        system, output = parse_template(content)
        assert system, f"Template {name} has no system prompt"
        assert output, f"Template {name} has no output template"

    @pytest.mark.parametrize("name", EXPECTED_TEMPLATES)
    def test_template_files_exist_on_disk(self, name):
        path = BUNDLED_DIR / f"{name}.md"
        assert path.is_file(), f"Template file missing: {path}"
