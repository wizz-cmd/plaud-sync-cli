"""Textual TUI for browsing Plaud recordings."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TuiError(Exception):
    """Raised when TUI cannot start."""


def _check_textual() -> None:
    """Check if textual is installed, raise helpful error if not."""
    try:
        import textual  # noqa: F401
    except ImportError:
        raise TuiError(
            "The TUI requires the 'textual' package.\n"
            "Install it with: pip install 'plaud-sync-cli[tui]'\n"
            "Or: pip install textual"
        )


def _format_date(ts: int | float) -> str:
    """Format a Unix timestamp (ms) to 'YYYY-MM-DD HH:MM'."""
    try:
        return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError, OverflowError):
        return "unknown"


def _truncate(text: str, width: int) -> str:
    """Truncate text to width, adding '..' if needed."""
    if len(text) <= width:
        return text
    return text[: width - 2] + ".."


def run_tui(
    files: list[dict],
    sync_folder: Path | None = None,
    api: Any = None,
) -> None:
    """Launch the interactive TUI.

    Args:
        files: List of file summary dicts from the API.
        sync_folder: Path to sync folder for reading local files.
        api: PlaudApiClient instance for on-demand fetching.
    """
    _check_textual()

    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static
    from textual.reactive import reactive

    # Sort by start_time descending
    files.sort(key=lambda f: f.get("start_time", 0), reverse=True)

    class RecordingItem(ListItem):
        """A single recording in the list."""

        def __init__(self, rec: dict) -> None:
            self.rec = rec
            ts = rec.get("start_time", 0)
            date = _format_date(ts) if isinstance(ts, (int, float)) and ts > 0 else "unknown"
            title = rec.get("file_name") or rec.get("title") or "Untitled"
            label = f"{date}  {_truncate(title, 40)}"
            super().__init__(Label(label), id=f"rec-{rec.get('file_id', rec.get('id', 'x'))}")

    class PreviewPanel(Static):
        """Right panel showing recording preview."""

        content: reactive[str] = reactive("Select a recording to preview.")

        def render(self) -> str:
            return self.content

    class PlaudTui(App):
        """Plaud recording browser."""

        CSS = """
        #main {
            layout: horizontal;
            height: 1fr;
        }
        #list-panel {
            width: 40%;
            min-width: 30;
            border-right: solid $accent;
        }
        #preview-panel {
            width: 60%;
            padding: 1 2;
            overflow-y: auto;
        }
        #search-input {
            dock: top;
            display: none;
        }
        #search-input.visible {
            display: block;
        }
        ListView {
            height: 1fr;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("/", "search", "Search"),
            Binding("escape", "clear_search", "Clear", show=False),
            Binding("e", "export", "Export"),
        ]

        TITLE = "Plaud Recordings"

        def __init__(self) -> None:
            super().__init__()
            self._all_files = files
            self._filtered_files = list(files)

        def compose(self) -> ComposeResult:
            yield Header()
            yield Input(placeholder="Search...", id="search-input")
            with Horizontal(id="main"):
                with Vertical(id="list-panel"):
                    yield ListView(
                        *[RecordingItem(f) for f in self._filtered_files],
                        id="rec-list",
                    )
                yield PreviewPanel(id="preview-panel")
            yield Footer()

        def on_list_view_selected(self, event: ListView.Selected) -> None:
            """Show preview when a recording is selected."""
            item = event.item
            if not isinstance(item, RecordingItem):
                return
            self._show_preview(item.rec)

        def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
            """Show preview when highlighting changes."""
            item = event.item
            if not isinstance(item, RecordingItem):
                return
            self._show_preview(item.rec)

        def _show_preview(self, rec: dict) -> None:
            """Load and display preview for a recording."""
            preview = self.query_one("#preview-panel", PreviewPanel)
            file_id = rec.get("file_id") or rec.get("id", "?")
            title = rec.get("file_name") or rec.get("title") or "Untitled"

            # Try to read from local sync folder
            content = self._read_local(file_id)
            if content:
                preview.content = content
                return

            # Show basic info
            ts = rec.get("start_time", 0)
            date = _format_date(ts) if isinstance(ts, (int, float)) and ts > 0 else "unknown"
            lines = [
                f"# {title}",
                f"",
                f"**Date:** {date}",
                f"**ID:** {file_id}",
                f"",
                f"_Not synced locally. Press 'e' to export._",
            ]
            preview.content = "\n".join(lines)

        def _read_local(self, file_id: str) -> str | None:
            """Try to read a synced markdown file by file_id."""
            if not sync_folder or not sync_folder.exists():
                return None
            for md_file in sync_folder.glob("*.md"):
                try:
                    text = md_file.read_text()
                    if f"file_id: {file_id}" in text[:500]:
                        return text
                except OSError:
                    continue
            return None

        def action_search(self) -> None:
            """Toggle search input."""
            search = self.query_one("#search-input", Input)
            search.add_class("visible")
            search.focus()

        def action_clear_search(self) -> None:
            """Clear search and show all recordings."""
            search = self.query_one("#search-input", Input)
            search.remove_class("visible")
            search.value = ""
            self._apply_filter("")

        def on_input_changed(self, event: Input.Changed) -> None:
            """Filter list as user types."""
            if event.input.id == "search-input":
                self._apply_filter(event.value)

        def _apply_filter(self, query: str) -> None:
            """Filter recording list by search query."""
            query = query.lower().strip()
            lv = self.query_one("#rec-list", ListView)
            lv.clear()
            for f in self._all_files:
                title = (f.get("file_name") or f.get("title") or "").lower()
                if not query or query in title:
                    lv.append(RecordingItem(f))

        def action_export(self) -> None:
            """Export current recording to sync folder."""
            if not sync_folder or not api:
                self.notify("Export requires sync folder and API access.", severity="error")
                return

            lv = self.query_one("#rec-list", ListView)
            if lv.highlighted_child is None:
                return
            item = lv.highlighted_child
            if not isinstance(item, RecordingItem):
                return

            rec = item.rec
            file_id = rec.get("file_id") or rec.get("id")
            if not file_id:
                return

            # Check if already synced
            if self._read_local(file_id):
                self.notify("Already synced.", severity="information")
                return

            try:
                from plaud_sync.hydrator import hydrate
                from plaud_sync.normalizer import normalize
                from plaud_sync.renderer import render_markdown
                from plaud_sync.sync import _make_filename, _resolve_collision

                detail = api.get_file_detail(file_id)
                detail = hydrate(detail)
                normalized = normalize(detail)
                markdown = render_markdown(normalized)

                sync_folder.mkdir(parents=True, exist_ok=True)
                filename = _make_filename("plaud-{date}-{title}", normalized)
                filename = _resolve_collision(sync_folder, filename)
                (sync_folder / filename).write_text(markdown)
                self.notify(f"Exported: {filename}")
                self._show_preview(rec)
            except Exception as e:
                self.notify(f"Export failed: {e}", severity="error")

    app = PlaudTui()
    app.run()
