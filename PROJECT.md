# PROJECT.md — Plaud Sync CLI

**Status:** aktiv
**Repo:** https://github.com/wizz-cmd/plaud-sync-cli
**Plattform:** dev (`~/projects/plaud-sync-cli/`)
**Sprache:** Python 3.10+ (stdlib only → ab v2: textual, optional LLM)
**Letzte Aktivität:** 2026-03-23

---

## Übersicht

Standalone CLI zum Sync von Plaud.ai Recordings nach lokalen Markdown-Dateien. Fork/Replatform von `leonardsellem/plaud-sync-for-obsidian` — kein Obsidian nötig.

## Aktueller Stand

### v1 — DONE ✅
- Python-Rewrite komplett (8 Module, 109 Tests grün)
- stdlib only, keine externen Dependencies
- CLI: `validate`, `sync` Subcommands
- Incremental Sync via Checkpoint
- Content Hydration (Transcripts + Summaries)
- Retry mit Exponential Backoff
- Cloudflare User-Agent Fix (98b7ebc)
- Token eingerichtet, 130 Recordings initial gesynct
- Cron alle 3h auf anna → `Ingest/meetings/plaud/`

### v2 — IN ARBEIT 🔧

#### Feature 1: `--period / -p` (Zeitraum-Filter)
hledger-style Syntax für alle Subcommands:
- `"2026-03"` (ganzer Monat)
- `"2026-03-01..2026-03-15"` (Zeitraum)
- `"thisweek"`, `"lastmonth"`, `"last7days"` (relative Ausdrücke)
- Filter auf `start_time` der Recordings
- Gilt für: `sync`, `list` (neu), `tui`

#### Feature 2: `tui` Subcommand (interaktiver Browser)
- Framework: `textual` (Python TUI)
- Layout: Recording-Liste links, Transcript-Vorschau rechts
- Navigation: Pfeiltasten, `/` Suche, `Enter` öffnen, `e` Export, `a` Analyse
- Kombinierbar mit `-p` für Zeitraum-Filter

#### Feature 3: Transcript-Analyse + Template Library
- Neuer Subcommand: `analyze <file-or-id>`
- Standard-Template: Zusammenfassung, Teilnehmer, Entscheidungen, Action Items, Offene Fragen
- Template Library in `~/.config/plaud-sync/templates/`
- Mitgelieferte Templates: `default.md`, `action-items.md`, `executive-summary.md`
- Ad-hoc Prompts: `--prompt "Fasse die Budgetdiskussion zusammen"`
- LLM-Backend konfigurierbar: OpenAI/Anthropic/local (Key in Config)
- Optionale Dependency — CLI funktioniert ohne LLM, nur `analyze` braucht es

#### Feature 4: User Guide
- `docs/USER-GUIDE.md`
- Zielgruppe: Andrea (macOS, eigener Plaud Account, kein Dev-Background)
- Schritt-für-Schritt: Homebrew → Python → git clone → Token → Sync → TUI
- Template-Erstellung erklärt

### Architektur-Änderungen v1 → v2
- `pyproject.toml` + `pip install -e .` statt roher Python-Aufruf
- Neue Dependencies: `textual` (TUI), LLM-SDK optional
- Neues Modul: `plaud_sync/period.py` (Zeitraum-Parser)
- Neues Modul: `plaud_sync/tui.py` (Textual App)
- Neues Modul: `plaud_sync/analyze.py` (Template Engine + LLM)
- Neuer Ordner: `templates/` (mitgelieferte Analyse-Templates)
- Neuer Ordner: `docs/` (User Guide)

---

## Konfiguration

**Token (dev):** `~/.secrets/plaud.txt`
**Token (anna):** `~/.secrets/plaud.txt`
**Token Ablauf:** ~November 2026
**API Domain:** `https://api.plaud.ai`
**Sync-Ziel:** `/home/anna/localvault/Chris Notes/Ingest/meetings/plaud/`
**Cron:** alle 3h (OpenClaw Cron Job `79316ff6`)

---

## Projekt-Map

| Was | Wo | System |
|-----|----|--------|
| Repo + PROJECT.md | `~/projects/plaud-sync-cli/` | dev |
| GitHub | `wizz-cmd/plaud-sync-cli` | github.com |
| Lokaler Clone (Sync) | `/home/anna/plaud-sync-cli/` | anna |
| Obsidian-Doku | `1. Projects/plaud-sync-cli/` | Obsidian Vault |
| Memory Anchor | `memory/reference/plaud-sync-cli.md` | anna-ai |
| Verweis | `~/clawd/projects/plaud-sync-cli/` | anna-ai |
| Token | `~/.secrets/plaud.txt` | dev + anna |

---

*Erstellt: 2026-03-07*
*Aktualisiert: 2026-03-23 von Anna*
