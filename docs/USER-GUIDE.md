# Plaud Sync CLI — User Guide

Plaud Sync CLI holt deine Plaud.ai-Aufnahmen als Markdown-Dateien auf deinen Computer. Du kannst sie durchsuchen, analysieren und lokal archivieren — ganz ohne Cloud-Abhängigkeit.

---

## 1. Voraussetzungen

Du brauchst:

- **macOS** (oder Linux)
- **Python 3.10 oder neuer**
- **Git** (zum Herunterladen des Codes)

### Python installieren (macOS)

Falls du Python noch nicht hast, installiere es über Homebrew:

```bash
# Homebrew installieren (falls noch nicht vorhanden)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python installieren
brew install python@3.12
```

Prüfe, ob es geklappt hat:

```bash
python3 --version
```

Du solltest etwas wie `Python 3.12.x` sehen.

### Git installieren (macOS)

```bash
brew install git
```

---

## 2. Installation

### Code herunterladen

```bash
cd ~/projects
git clone https://github.com/wizz-cmd/plaud-sync-cli.git
cd plaud-sync-cli
```

### Installieren

Für die Basis-Version (nur Sync):

```bash
pip install -e .
```

Für alle Features (TUI + Analyse):

```bash
pip install -e '.[all]'
```

Prüfe, ob es funktioniert:

```bash
plaud-sync --version
```

---

## 3. Token extrahieren

Du brauchst dein Plaud.ai API-Token. So bekommst du es:

1. Öffne **Google Chrome** oder **Firefox**
2. Gehe zu [https://app.plaud.ai](https://app.plaud.ai) und melde dich an
3. Öffne die **Entwicklertools** (Rechtsklick → „Untersuchen" → Tab **Netzwerk**)
4. Klicke in der Plaud-App auf irgendeine Aufnahme
5. In den Entwicklertools siehst du Netzwerk-Anfragen. Klicke auf eine, die an `api.plaud.ai` geht
6. Unter **Request Headers** findest du `Authorization: Bearer eyJ...`
7. Kopiere alles nach `Bearer ` — das ist dein Token

### Token speichern

```bash
mkdir -p ~/.secrets
nano ~/.secrets/plaud.txt
```

Füge dein Token ein (die lange Zeichenkette, die mit `eyJ` beginnt), speichere mit `Ctrl+O`, `Enter`, `Ctrl+X`.

Schütze die Datei:

```bash
chmod 600 ~/.secrets/plaud.txt
```

---

## 4. Erster Sync

Erstelle einen Ordner für deine Aufnahmen und starte den Sync:

```bash
mkdir -p ~/Documents/Plaud
plaud-sync sync --vault ~/Documents/Plaud --verbose
```

Was passiert:
- Plaud Sync holt die Liste aller deiner Aufnahmen von Plaud.ai
- Für jede Aufnahme wird eine Markdown-Datei erstellt
- Die Dateien landen in `~/Documents/Plaud/Plaud/`
- Jede Datei enthält: Titel, Datum, Zusammenfassung, Highlights und Transcript

Beim nächsten Mal werden nur neue Aufnahmen geholt (inkrementeller Sync).

### Token prüfen

Falls du unsicher bist, ob dein Token noch gültig ist:

```bash
plaud-sync validate
```

---

## 5. Aufnahmen auflisten

Du kannst Aufnahmen auflisten, ohne sie zu synchronisieren:

```bash
# Alle Aufnahmen
plaud-sync list

# Nur dieser Monat
plaud-sync list -p thismonth

# Nur letzte Woche
plaud-sync list -p lastweek

# Bestimmter Zeitraum
plaud-sync list -p "2026-03-01..2026-03-15"
```

Der `-p` Filter funktioniert auch mit `sync`:

```bash
# Nur Aufnahmen von März 2026 synchronisieren
plaud-sync sync --vault ~/Documents/Plaud -p 2026-03
```

### Unterstützte Zeiträume

| Format | Beispiel | Bedeutung |
|--------|----------|-----------|
| Monat | `2026-03` | Ganzer März 2026 |
| Tag | `2026-03-15` | Nur der 15. März |
| Bereich | `2026-03-01..2026-03-15` | 1. bis 15. März |
| Heute | `today` | Nur heute |
| Gestern | `yesterday` | Nur gestern |
| Diese Woche | `thisweek` | Montag bis Sonntag |
| Letzte Woche | `lastweek` | Letzte Woche (Mo–So) |
| Dieser Monat | `thismonth` | Aktueller Monat |
| Letzter Monat | `lastmonth` | Vorheriger Monat |
| Letzte 7 Tage | `last7days` | Die letzten 7 Tage |
| Letzte 30 Tage | `last30days` | Die letzten 30 Tage |

---

## 6. Regelmäßiger Sync (Automatisch)

### macOS: LaunchAgent einrichten

Erstelle die Datei `~/Library/LaunchAgents/com.plaud-sync.plist`:

```bash
mkdir -p ~/Library/LaunchAgents
cat > ~/Library/LaunchAgents/com.plaud-sync.plist << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.plaud-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/plaud-sync</string>
        <string>sync</string>
        <string>--vault</string>
        <string>/Users/DEIN_USERNAME/Documents/Plaud</string>
    </array>
    <key>StartInterval</key>
    <integer>10800</integer>
    <key>StandardOutPath</key>
    <string>/tmp/plaud-sync.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/plaud-sync-error.log</string>
</dict>
</plist>
PLIST
```

**Wichtig:** Ersetze `DEIN_USERNAME` durch deinen macOS-Benutzernamen.

Aktiviere den Job:

```bash
launchctl load ~/Library/LaunchAgents/com.plaud-sync.plist
```

Jetzt synchronisiert Plaud Sync automatisch alle 3 Stunden.

Zum Deaktivieren:

```bash
launchctl unload ~/Library/LaunchAgents/com.plaud-sync.plist
```

---

## 7. TUI benutzen (Interaktiver Browser)

Der TUI-Modus zeigt dir eine interaktive Übersicht deiner Aufnahmen.

### Voraussetzung

```bash
pip install -e '.[tui]'
```

### Starten

```bash
plaud-sync tui --vault ~/Documents/Plaud
```

Oder mit Zeitfilter:

```bash
plaud-sync tui --vault ~/Documents/Plaud -p thismonth
```

### Bedienung

| Taste | Funktion |
|-------|----------|
| `↑` `↓` | Aufnahme auswählen |
| `/` | Suche öffnen (nach Titel filtern) |
| `Escape` | Suche schließen |
| `e` | Aufnahme exportieren (als Markdown speichern) |
| `q` | Beenden |

Links siehst du die Liste deiner Aufnahmen, rechts die Vorschau der ausgewählten Aufnahme.

---

## 8. Transcripts analysieren

Du kannst Transcripts mit einem KI-Modell (z.B. GPT-4) analysieren lassen.

### LLM konfigurieren

Erstelle oder ergänze `~/.config/plaud-sync/config.json`:

```bash
mkdir -p ~/.config/plaud-sync
nano ~/.config/plaud-sync/config.json
```

Füge folgendes ein:

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "apiKeyFile": "~/.secrets/openai.txt"
  }
}
```

Speichere deinen OpenAI API-Key:

```bash
nano ~/.secrets/openai.txt
```

Füge deinen Key ein (beginnt mit `sk-`), speichere und schließe.

### Analyse starten

```bash
# Mit Standard-Template (Zusammenfassung, Teilnehmer, Entscheidungen, Action Items)
plaud-sync analyze ~/Documents/Plaud/Plaud/plaud-2026-03-23-team-meeting.md

# Mit bestimmtem Template
plaud-sync analyze datei.md --template action-items

# Mit zusätzlichem Fokus
plaud-sync analyze datei.md --prompt "Fokus auf Budgetdiskussion"

# Template + Zusatz kombiniert
plaud-sync analyze datei.md --template executive-summary --prompt "Fokus auf Roche-Projekt"
```

### Verfügbare Templates anzeigen

```bash
# Alle Templates auflisten
plaud-sync templates list

# Ein Template ansehen
plaud-sync templates show default
```

### Eigenes Template erstellen

Erstelle eine Markdown-Datei in `~/.config/plaud-sync/templates/`:

```bash
mkdir -p ~/.config/plaud-sync/templates
nano ~/.config/plaud-sync/templates/mein-template.md
```

Format:

```markdown
{instructions}
Deine Anweisungen an die KI hier. Zum Beispiel:
Erstelle eine kurze Zusammenfassung mit Fokus auf technische Details.
{/instructions}

## Technische Zusammenfassung

{Dein gewünschtes Ausgabeformat hier}

## Technische Entscheidungen

{Liste der technischen Entscheidungen}
```

Dann nutze es so:

```bash
plaud-sync analyze datei.md --template mein-template
```

Eigene Templates mit dem gleichen Namen wie ein mitgeliefertes Template überschreiben das Original.

---

## 9. Troubleshooting

### "Token file not found"

Du hast noch kein Token gespeichert. Folge Abschnitt 3 oben.

### "Authentication failed"

Dein Token ist abgelaufen. Hole ein neues Token (Abschnitt 3) und ersetze den Inhalt von `~/.secrets/plaud.txt`.

### "python3: command not found"

Python ist nicht installiert. Folge den Schritten in Abschnitt 1.

### "Permission denied"

Stelle sicher, dass du Schreibrechte auf den Ausgabeordner hast:

```bash
ls -la ~/Documents/Plaud/
```

### "No module named 'plaud_sync'"

Du bist nicht im richtigen Ordner, oder hast `pip install -e .` noch nicht ausgeführt:

```bash
cd ~/projects/plaud-sync-cli
pip install -e .
```

### "textual not installed"

Installiere die TUI-Abhängigkeit:

```bash
pip install -e '.[tui]'
```

### "LLM not configured"

Für die Analyse-Funktion brauchst du eine LLM-Konfiguration. Folge Abschnitt 8 oben.

### "httpx not installed"

Installiere die Analyse-Abhängigkeit:

```bash
pip install -e '.[analyze]'
```

### Sync läuft, aber es kommen keine neuen Dateien

- Prüfe, ob neue Aufnahmen auf [app.plaud.ai](https://app.plaud.ai) vorhanden sind
- Versuche es mit `--verbose` für mehr Details: `plaud-sync sync --vault ~/Documents/Plaud --verbose`
- Der Sync überspringt Aufnahmen, die bereits synchronisiert wurden (inkrementell)

---

## Hilfe

```bash
# Allgemeine Hilfe
plaud-sync --help

# Hilfe zu einem Befehl
plaud-sync sync --help
plaud-sync list --help
plaud-sync tui --help
plaud-sync analyze --help
```
