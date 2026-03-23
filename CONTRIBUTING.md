# CONTRIBUTING.md — Plaud Sync CLI

## Standards

- **Python 3.10+**, Type Hints auf allen public Functions
- **Formatting:** Black-kompatibel (88 chars), aber kein Black als Dependency
- **Imports:** stdlib first, then third-party, then local — alphabetisch
- **Tests:** pytest, im `test/` Ordner, Dateiname `test_<module>.py`
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)
- **Exit Codes:** 0 = OK, 1 = Runtime Error, 2 = Auth Error (sysexits-inspired)

## Architektur

```
plaud_sync/
  __init__.py
  cli.py          # Entrypoint, Subcommand-Routing
  api.py          # Plaud API Client
  sync.py         # Sync-Logik (Dateien schreiben)
  retry.py        # Retry + Backoff
  period.py       # Zeitraum-Parser (v2)
  tui.py          # Textual TUI (v2, lazy import)
  analyze.py      # Template Engine + LLM (v2, lazy import)
templates/        # Mitgelieferte Analyse-Templates
docs/             # User Guide
test/             # Tests
```

## Prinzipien

1. **Robust & Defensive:** Fail early, fail loud. Atomic writes für Sync-Dateien.
2. **Idempotent:** Sync darf beliebig oft laufen ohne Duplikate.
3. **Graceful Degradation:** Fehlende optionale Dependencies → klare Fehlermeldung, kein Crash.
4. **Keine Magie:** Explizite Config, keine versteckten Defaults die überraschen.
5. **Testbar:** `--dry-run` wo sinnvoll, alles mockbar, keine globalen Seiteneffekte.
