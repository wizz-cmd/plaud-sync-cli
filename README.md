# plaud-sync-cli

Standalone CLI tool to sync [Plaud.ai](https://plaud.ai) recordings to local markdown files. Replatformed from [plaud-sync-for-obsidian](https://github.com/leonardsellem/plaud-sync-for-obsidian) by Leonard Sellem.

No Obsidian dependency required -- works as a plain Python CLI, ideal for cron jobs and automation.

## Features

- Syncs Plaud recordings to local markdown files with YAML frontmatter
- Incremental sync via checkpoint (only fetches new recordings)
- Content hydration: fetches full transcripts and summaries from signed URLs
- Retry with exponential backoff for transient API errors
- Filename collision resolution
- Cron-friendly: proper exit codes, no prompts, quiet by default
- Zero external dependencies (stdlib only)

## Requirements

- Python 3.10+

## Installation

```bash
git clone https://github.com/wizz-cmd/plaud-sync-cli.git
cd plaud-sync-cli
```

No `pip install` needed -- runs directly with Python.

## Setup

### 1. Get your Plaud API token

Log into the Plaud web app, open browser DevTools, and grab the Bearer token from any API request.

### 2. Save the token

```bash
mkdir -p ~/.secrets
echo 'YOUR_PLAUD_TOKEN' > ~/.secrets/plaud.txt
chmod 600 ~/.secrets/plaud.txt
```

### 3. (Optional) Create a config file

```bash
mkdir -p ~/.config/plaud-sync
cp config.example.json ~/.config/plaud-sync/config.json
# Edit as needed
```

## Usage

### Validate your token

```bash
python3 -m plaud_sync.cli validate
```

### Sync recordings

```bash
python3 -m plaud_sync.cli sync
```

### With options

```bash
python3 -m plaud_sync.cli sync \
  --vault /path/to/notes \
  --folder Ingest/meetings/plaud \
  --token-file ~/.secrets/plaud.txt \
  --verbose
```

### CLI Options

| Option | Description | Default |
|---|---|---|
| `--vault <path>` | Base directory for output | Current directory |
| `--folder <name>` | Subfolder for synced notes | From config or `Plaud` |
| `--token-file <path>` | Path to API token file | `~/.secrets/plaud.txt` |
| `--config <path>` | Config file path | `~/.config/plaud-sync/config.json` |
| `--verbose` | Enable verbose logging to stderr | Off |

### Cron setup

```bash
# Sync every hour
0 * * * * cd /path/to/notes && python3 -m plaud_sync.cli sync --vault /path/to/notes 2>> /var/log/plaud-sync.log
```

Exit codes:
- `0` = success
- `1` = sync completed with failures, or runtime error
- `2` = authentication failure

## Config

Copy `config.example.json` to `~/.config/plaud-sync/config.json`:

```json
{
  "apiDomain": "https://api.plaud.ai",
  "syncFolder": "Plaud",
  "updateExisting": true,
  "filenamePattern": "plaud-{date}-{title}"
}
```

## Checkpoint

Sync state is stored in `.plaud-sync-state.json` inside the sync folder. The checkpoint only advances when all files in a batch sync successfully (fail-safe).

## Output Format

Each recording becomes a markdown file:

```markdown
---
source: plaud
type: recording
file_id: abc123
title: "Team Standup"
date: 2024-01-15
duration: 5 min
---

# Team Standup

## Summary
Meeting discussed project updates...

## Highlights
- Deadline moved to Friday
- New hire starting Monday

## Transcript
Alice: Good morning everyone...
Bob: Morning! Let's get started...
```

## Development

```bash
python3 -m pytest test/ -v   # Run tests
python3 -m plaud_sync.cli --help   # Show CLI help
```

## License

MIT -- Original work by [Leonard Sellem](https://github.com/leonardsellem/plaud-sync-for-obsidian).
