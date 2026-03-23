# Testplan: Plaud Sync CLI auf CG MacBook

## Voraussetzungen

```bash
# Python 3.10+ prüfen
python3 --version

# Falls nicht vorhanden: Homebrew + Python
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.12
```

## 1. Installation

```bash
cd ~/projects
git clone https://github.com/wizz-cmd/plaud-sync-cli.git
cd plaud-sync-cli
pip install -e '.[all]'   # Basis + TUI + Analyze
```

## 2. Token einrichten

```bash
mkdir -p ~/.secrets
echo 'DEIN_TOKEN' > ~/.secrets/plaud.txt
chmod 600 ~/.secrets/plaud.txt
```

Token holen: web.plaud.ai → DevTools Console → `localStorage.getItem("tokenstr")`

## 3. Tests ausführen

```bash
python3 -m pytest test/ -v
# Erwartung: 226 passed, 1 skipped
```

## 4. Token validieren

```bash
plaud-sync validate --token-file ~/.secrets/plaud.txt --verbose
# Erwartung: "Token is valid."
```

## 5. Sync testen (Temp-Ordner)

```bash
mkdir -p /tmp/plaud-test
plaud-sync sync --vault /tmp/plaud-test --folder plaud --token-file ~/.secrets/plaud.txt --verbose
# Erwartung: ~124 created, 6 failed (Recordings ohne Titel)
```

### Prüfen:

```bash
ls /tmp/plaud-test/plaud/ | wc -l
head -20 /tmp/plaud-test/plaud/2026-03-23*.md
```

## 6. Period-Filter testen

```bash
plaud-sync sync --vault /tmp/plaud-test --folder plaud-march -p "2026-03" --token-file ~/.secrets/plaud.txt --verbose
plaud-sync list --vault /tmp/plaud-test --folder plaud -p "last7days" --token-file ~/.secrets/plaud.txt
```

## 7. Journal testen

```bash
# Stats
plaud-sync journal --vault /tmp/plaud-test --folder plaud --stats

# Obsidian-Rendering
plaud-sync journal --vault /tmp/plaud-test --folder plaud --render-obsidian /tmp/plaud-test/Meeting-Journal.md
head -30 /tmp/plaud-test/Meeting-Journal.md
```

## 8. TUI testen

```bash
plaud-sync tui --vault /tmp/plaud-test --folder plaud --token-file ~/.secrets/plaud.txt
# ↑↓ Navigate, Enter=Open, /=Search, q=Quit
```

## 9. Analyze testen (braucht OpenAI Key)

```bash
mkdir -p ~/.config/plaud-sync
cat > ~/.config/plaud-sync/config.json << 'CONF'
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "apiKeyFile": "~/.secrets/openai.txt"
  }
}
CONF

plaud-sync analyze /tmp/plaud-test/plaud/2026-03-23*.md
plaud-sync analyze /tmp/plaud-test/plaud/2026-03-23*.md --template action-items
plaud-sync analyze /tmp/plaud-test/plaud/2026-03-23*.md --prompt "Welche Übergaben wurden besprochen?"
plaud-sync templates list
```

## 10. Aufräumen

```bash
rm -rf /tmp/plaud-test
```

## Erwartete Ergebnisse

| Test | Erwartung |
|------|-----------|
| pytest | 226 passed, 1 skipped |
| validate | Token is valid |
| sync | ~124 created, 6 failed |
| period | Korrekte Filterung nach Zeitraum |
| journal | JSONL + Stats korrekt |
| tui | Interaktive Liste, Transcript-Preview |
| analyze | LLM-generierte Zusammenfassung |

## Bekannte Einschränkungen

- 6 Recordings ohne Titel schlagen fehl (Plaud API liefert `None`)
- TUI braucht Terminal mit Unicode-Support (iTerm2, Terminal.app — ok)
- Analyze braucht konfigurierten LLM-Provider
