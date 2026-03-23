# CLAUDE.md — Plaud Sync CLI

## Projekt

Standalone Python CLI zum Sync von Plaud.ai Recordings nach Markdown. Lies PROJECT.md für den vollen Kontext.

## Regeln

- Python 3.10+, Type Hints überall
- Bestehende Tests MÜSSEN weiterhin grün sein (`python3 -m pytest test/ -v`)
- Neue Features MÜSSEN Tests haben
- Keine Breaking Changes an bestehendem CLI-Interface
- `pyproject.toml` für Package-Management (kein setup.py)
- Git-Commits: conventional commits (feat:, fix:, docs:), atomar pro Feature

## Dein Auftrag — v2 Features

### 1. Zeitraum-Filter `--period / -p`

**Neues Modul:** `plaud_sync/period.py`

Implementiere einen hledger-inspirierten Zeitraum-Parser:

```python
def parse_period(spec: str) -> tuple[datetime, datetime]:
    """Parse period spec into (start, end) datetime range."""
```

**Unterstützte Formate:**
- ISO-Monat: `"2026-03"` → 1. März 00:00 bis 1. April 00:00
- ISO-Tag: `"2026-03-15"` → ganzer Tag
- Bereich: `"2026-03-01..2026-03-15"` → Start bis End (End inklusive, also bis 16. 00:00)
- Relative: `"today"`, `"yesterday"`, `"thisweek"`, `"lastweek"`, `"thismonth"`, `"lastmonth"`, `"thisquarter"`, `"lastquarter"`, `"last7days"`, `"last30days"`, `"last90days"`
- Woche = Montag bis Sonntag (europäisch)

**Integration:**
- `--period / -p` Flag für `sync`, `list` (neu), `tui`
- Filter in `api.py` oder `sync.py`: Recordings nach `start_time` (Unix timestamp) filtern
- Neuer Subcommand `list`: wie `sync` aber nur auflisten, nicht schreiben

**Tests:** `test/test_period.py` — jeden Format-Typ testen, Edge Cases (Jahreswechsel, Schaltjahr)

### 2. TUI Subcommand

**Neues Modul:** `plaud_sync/tui.py`
**Dependency:** `textual` (in pyproject.toml als optional: `pip install plaud-sync-cli[tui]`)

**Layout:**
```
┌─ Recordings ──────────┬─ Preview ────────────────────┐
│ 2026-03-23 Abschied.. │ # Abschiedsgespräch          │
│ 2026-03-23 Go-to-Ma.. │                              │
│ 2026-03-20 Beratung.. │ ## Zusammenfassung            │
│ > 2026-03-19 Roche..  │ Meeting zu Roche Beyond...    │
│ 2026-03-17 All-Hand.. │                              │
│                       │ ## Transcript                 │
│                       │ Chris: Guten Morgen...        │
├───────────────────────┴──────────────────────────────┤
│ ↑↓ Navigate  / Search  Enter Open  e Export  a Analyze│
└──────────────────────────────────────────────────────┘
```

**Funktionen:**
- Lade Recordings von API (mit optionalem `-p` Filter)
- Linke Liste: Datum + Titel (gekürzt), sortiert nach Datum desc
- Rechte Preview: Markdown-Inhalt der ausgewählten Recording (lokal aus Sync-Ordner lesen, oder on-demand von API)
- `/` → Suchfeld (filtert Titel)
- `Enter` → Vollansicht (scrollbar)
- `e` → Export: Schreibt das Recording als .md in den Sync-Ordner (falls noch nicht gesynct)
- `a` → Analyze: Öffnet Analyse-Dialog (Template-Auswahl oder freier Prompt)
- `q` → Quit

**Graceful Degradation:** Wenn `textual` nicht installiert → klare Fehlermeldung mit Installationshinweis

### 3. Transcript-Analyse + Template Library

**Neues Modul:** `plaud_sync/analyze.py`

**Templates:**
- Verzeichnis: `templates/` im Repo (mitgeliefert) + `~/.config/plaud-sync/templates/` (benutzerdefiniert)
- Format: Markdown mit `{instructions}` Block am Anfang (wird als System-Prompt verwendet)
- Benutzer-Templates überschreiben mitgelieferte gleichen Namens

**Mitgelieferte Templates:**

`templates/default.md`:
```markdown
{instructions}
Analysiere das folgende Meeting-Transcript. Antworte auf Deutsch, wenn das Transcript überwiegend deutsch ist, sonst auf Englisch.
{/instructions}

## Zusammenfassung
{3-5 Sätze, die den Kern des Meetings erfassen}

## Teilnehmer
{Liste der identifizierbaren Teilnehmer mit Rolle falls erkennbar}

## Kernentscheidungen
{Bullet Points der getroffenen Entscheidungen}

## Action Items
{Wer | Was | Bis Wann (falls genannt)}

## Offene Fragen
{Ungeklärte Punkte, die Nachverfolgung brauchen}
```

`templates/action-items.md`:
```markdown
{instructions}
Extrahiere ausschließlich Action Items aus dem Transcript. Sei präzise bei Verantwortlichkeiten und Deadlines.
{/instructions}

## Action Items

| # | Verantwortlich | Aufgabe | Deadline | Kontext |
|---|---------------|---------|----------|---------|
```

`templates/executive-summary.md`:
```markdown
{instructions}
Erstelle eine Executive Summary für Führungskräfte. Maximal 10 Sätze. Fokus auf strategische Entscheidungen, Risiken und nächste Schritte.
{/instructions}

## Executive Summary

{Kompakte Zusammenfassung für Management-Ebene}

## Strategische Implikationen

{Was bedeutet das für die Organisation?}

## Nächste Schritte

{Priorisierte Liste}
```

**CLI:**
```bash
plaud-sync analyze <datei-oder-id>                        # Standard-Template
plaud-sync analyze <datei> --template action-items         # Bestimmtes Template
plaud-sync analyze <datei> --prompt "Budgetdiskussion"     # Ad-hoc
plaud-sync analyze <datei> --template exec --prompt "Fokus auf Roche"  # Template + Zusatz
plaud-sync templates list                                  # Verfügbare Templates
plaud-sync templates show <name>                           # Template anzeigen
```

**LLM-Konfiguration in `config.json`:**
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "apiKeyFile": "~/.secrets/openai.txt"
  }
}
```

Unterstützte Provider: `openai` (API-kompatibel, also auch local/ollama via base_url). Anthropic als Stretch Goal.

**Kein LLM konfiguriert → klare Fehlermeldung**, kein Crash.

### 4. User Guide

**Datei:** `docs/USER-GUIDE.md`

**Zielgruppe:** Andrea — Mac-Nutzerin, kein Dev-Background, eigener Plaud Account.

**Gliederung:**
1. Was ist Plaud Sync CLI? (2 Sätze)
2. Voraussetzungen (macOS, Homebrew, Python — mit Installationsanleitung)
3. Installation (git clone, pip install)
4. Token extrahieren (Schritt für Schritt, welcher Browser, wo klicken)
5. Erster Sync (Befehl, was passiert, wo landen die Dateien)
6. Regelmäßiger Sync (Cron einrichten auf macOS via launchd — mit fertigem plist)
7. TUI benutzen (Starten, Navigieren, Suchen)
8. Transcripts analysieren (Template wählen, eigenes Template erstellen)
9. Troubleshooting (Token abgelaufen, kein Python, Permission denied)

**Stil:** Du-Anrede, kurze Sätze, Code-Blöcke mit Copy-Paste-fähigen Befehlen. Keine Fachbegriffe ohne Erklärung.

### Package Setup

**`pyproject.toml`:**
```toml
[project]
name = "plaud-sync-cli"
version = "2.0.0"
description = "Sync Plaud.ai recordings to local Markdown files"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
tui = ["textual>=0.40"]
analyze = ["httpx>=0.25"]
all = ["textual>=0.40", "httpx>=0.25"]

[project.scripts]
plaud-sync = "plaud_sync.cli:main"
```

So kann man `pip install -e .` für Basis, `pip install -e '.[tui]'` für TUI, `pip install -e '.[all]'` für alles.

## Architektur-Regeln

- `period.py` ist ein reiner Parser — keine API-Calls, keine Side Effects
- `tui.py` importiert `textual` nur beim Aufruf (lazy import), nicht beim Modul-Load
- `analyze.py` importiert LLM-SDK nur beim Aufruf (lazy import)
- Alle neuen Module folgen dem bestehenden Pattern: Logging via `logging`, Fehler als eigene Exception-Klassen
- `cli.py` bleibt der einzige Entrypoint — neue Subcommands dort registrieren
- Bestehende `sync`/`validate` Subcommands NICHT ändern (außer `--period` Flag hinzufügen)

## Tests

- `test/test_period.py` — Zeitraum-Parser (alle Formate, Edge Cases)
- `test/test_tui.py` — TUI-Komponenten (mindestens: App startet, Liste rendert)
- `test/test_analyze.py` — Template Loading, Prompt-Building (ohne echte API-Calls — mocken)
- `test/test_templates.py` — Mitgelieferte Templates sind valide, parseable
- Alle bestehenden Tests in `test/` MÜSSEN weiterhin grün sein

## Nicht im Scope

- Kein Upload zu Plaud (read-only)
- Kein eigener LLM/AI — nur API-Calls an externe Provider
- Kein GUI (nur TUI)
- Kein Auto-Update des Tokens
