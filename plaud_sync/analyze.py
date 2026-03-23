"""Template-based transcript analysis with LLM integration."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_INSTRUCTIONS_RE = re.compile(
    r"\{instructions\}\s*\n(.*?)\n\s*\{/instructions\}",
    re.DOTALL,
)

# Bundled templates ship with the package
_BUNDLED_DIR = Path(__file__).parent.parent / "templates"
# User templates override bundled ones
_USER_DIR = Path(os.path.expanduser("~/.config/plaud-sync/templates"))


class AnalyzeError(Exception):
    """Raised on analysis failures."""


class NoLlmConfigError(AnalyzeError):
    """Raised when no LLM provider is configured."""


def list_templates() -> list[dict[str, str]]:
    """List all available templates (bundled + user).

    User templates with the same name override bundled ones.

    Returns:
        List of dicts with 'name', 'path', 'source' keys.
    """
    templates: dict[str, dict[str, str]] = {}

    # Bundled first
    if _BUNDLED_DIR.is_dir():
        for f in sorted(_BUNDLED_DIR.glob("*.md")):
            name = f.stem
            templates[name] = {"name": name, "path": str(f), "source": "bundled"}

    # User overrides
    if _USER_DIR.is_dir():
        for f in sorted(_USER_DIR.glob("*.md")):
            name = f.stem
            templates[name] = {"name": name, "path": str(f), "source": "user"}

    return list(templates.values())


def load_template(name: str) -> str:
    """Load a template by name.

    Looks in user dir first, then bundled dir.

    Args:
        name: Template name (without .md extension).

    Returns:
        Template content as string.

    Raises:
        AnalyzeError: If template is not found.
    """
    # Strip .md if provided
    if name.endswith(".md"):
        name = name[:-3]

    # User dir first
    user_path = _USER_DIR / f"{name}.md"
    if user_path.is_file():
        return user_path.read_text()

    # Bundled
    bundled_path = _BUNDLED_DIR / f"{name}.md"
    if bundled_path.is_file():
        return bundled_path.read_text()

    raise AnalyzeError(
        f"Template not found: {name!r}\n"
        f"Available: {', '.join(t['name'] for t in list_templates())}"
    )


def parse_template(content: str) -> tuple[str, str]:
    """Parse a template into (system_prompt, output_template).

    The {instructions}...{/instructions} block becomes the system prompt.
    Everything else is the output template.

    Returns:
        Tuple of (system_prompt, output_template).
    """
    match = _INSTRUCTIONS_RE.search(content)
    if match:
        system_prompt = match.group(1).strip()
        output_template = (
            content[: match.start()] + content[match.end() :]
        ).strip()
    else:
        system_prompt = ""
        output_template = content.strip()
    return system_prompt, output_template


def build_prompt(
    transcript: str,
    template_name: str | None = None,
    extra_prompt: str | None = None,
) -> tuple[str, str]:
    """Build the full (system_prompt, user_message) for LLM analysis.

    Args:
        transcript: The transcript text to analyze.
        template_name: Name of template to use (default: "default").
        extra_prompt: Additional instructions to append.

    Returns:
        Tuple of (system_prompt, user_message).
    """
    template_content = load_template(template_name or "default")
    system_prompt, output_template = parse_template(template_content)

    if extra_prompt:
        system_prompt = f"{system_prompt}\n\nAdditional instructions: {extra_prompt}".strip()

    user_message = (
        f"Analyze the following transcript and respond using this format:\n\n"
        f"{output_template}\n\n"
        f"---\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )

    return system_prompt, user_message


def load_llm_config(config_path: str | None = None) -> dict[str, Any]:
    """Load LLM configuration from config.json.

    Looks for an 'llm' key in the config file.

    Returns:
        LLM config dict with 'provider', 'model', etc.

    Raises:
        NoLlmConfigError: If no LLM config is found.
    """
    path = Path(os.path.expanduser(config_path or "~/.config/plaud-sync/config.json"))

    if not path.exists():
        raise NoLlmConfigError(
            "No config file found. Create ~/.config/plaud-sync/config.json with an 'llm' section.\n"
            "Example:\n"
            '  {"llm": {"provider": "openai", "model": "gpt-4o", "apiKeyFile": "~/.secrets/openai.txt"}}'
        )

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise NoLlmConfigError(f"Failed to read config: {e}") from e

    llm = data.get("llm")
    if not isinstance(llm, dict) or not llm.get("provider"):
        raise NoLlmConfigError(
            "No 'llm' section in config.json. Add:\n"
            '  {"llm": {"provider": "openai", "model": "gpt-4o", "apiKeyFile": "~/.secrets/openai.txt"}}'
        )

    return llm


def _load_api_key(llm_config: dict[str, Any]) -> str:
    """Load API key from the file specified in config."""
    key_file = llm_config.get("apiKeyFile")
    if not key_file:
        raise AnalyzeError("No 'apiKeyFile' in LLM config.")

    path = Path(os.path.expanduser(key_file))
    if not path.exists():
        raise AnalyzeError(f"API key file not found: {path}")

    key = path.read_text().strip()
    if not key:
        raise AnalyzeError(f"API key file is empty: {path}")
    return key


def run_analysis(
    transcript: str,
    template_name: str | None = None,
    extra_prompt: str | None = None,
    config_path: str | None = None,
) -> str:
    """Run LLM analysis on a transcript.

    Args:
        transcript: The transcript text.
        template_name: Template name (default: "default").
        extra_prompt: Additional instructions.
        config_path: Path to config file.

    Returns:
        The LLM's response text.

    Raises:
        NoLlmConfigError: If LLM is not configured.
        AnalyzeError: On other failures.
    """
    llm_config = load_llm_config(config_path)
    api_key = _load_api_key(llm_config)

    provider = llm_config["provider"]
    model = llm_config.get("model", "gpt-4o")
    base_url = llm_config.get("baseUrl")

    system_prompt, user_message = build_prompt(transcript, template_name, extra_prompt)

    if provider == "openai":
        return _call_openai(api_key, model, system_prompt, user_message, base_url)
    else:
        raise AnalyzeError(f"Unsupported LLM provider: {provider!r}. Supported: openai")


def _call_openai(
    api_key: str,
    model: str,
    system_prompt: str,
    user_message: str,
    base_url: str | None = None,
) -> str:
    """Call OpenAI-compatible API using httpx."""
    try:
        import httpx
    except ImportError:
        raise AnalyzeError(
            "The 'httpx' package is required for analysis.\n"
            "Install it with: pip install 'plaud-sync-cli[analyze]'\n"
            "Or: pip install httpx"
        )

    url = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "messages": messages},
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        raise AnalyzeError(f"LLM API error: HTTP {e.response.status_code}") from e
    except (httpx.RequestError, KeyError, IndexError) as e:
        raise AnalyzeError(f"LLM request failed: {e}") from e
