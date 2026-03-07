# CLAUDE.md

## Project
Plaud Sync CLI - standalone CLI to sync Plaud.ai voice recordings into a local Obsidian vault folder.

## Goal
Replatform leonardsellem/plaud-sync-for-obsidian (TypeScript/Obsidian plugin) as a Python CLI tool. No Obsidian dependency. Syncs Plaud recordings to local markdown files with transcripts, AI summaries, and metadata.

## Source Reference
The original TypeScript source is at /tmp/plaud-source (already cloned). Study it to understand the Plaud API, data structures, and sync logic. Then rewrite in Python.

## Architecture
- plaud_sync/__init__.py
- plaud_sync/cli.py - CLI entry point (argparse)
- plaud_sync/api.py - Plaud API client (requests or urllib)
- plaud_sync/normalizer.py - Payload normalization
- plaud_sync/hydrator.py - Content hydration from signed URLs
- plaud_sync/renderer.py - Markdown rendering
- plaud_sync/sync.py - Incremental sync orchestration
- plaud_sync/config.py - Config file loading
- plaud_sync/retry.py - Retry with backoff
- test/ - pytest tests for each module
- config.example.json
- README.md, LICENSE

## Tech Stack
- Language: Python 3.10+ (MUST be Python, NOT TypeScript)
- Dependencies: stdlib only preferred. requests only if urllib is insufficient.
- Config: ~/.config/plaud-sync/config.json (+ CLI arg overrides)
- Secrets: Token from file (--token-file arg, default ~/.secrets/plaud.txt)
- State: .plaud-sync-state.json in target folder

## CLI Interface
- plaud-sync sync --vault /path/to/vault --folder Ingest/meetings/plaud --token-file ~/.secrets/plaud.txt
- plaud-sync validate --token-file ~/.secrets/plaud.txt
- plaud-sync sync --verbose (debug output)

## Conventions
- PEP 8, type hints, docstrings for public functions
- Proper exit codes: 0=success, 1=error, 2=auth failure
- Quiet by default (cron-friendly), --verbose for debug output
- No hardcoded paths - everything via args or config
- Incremental sync: only fetch recordings newer than last checkpoint
- Idempotent: re-running should not create duplicates (use file_id in frontmatter)

## Markdown Output Format (per recording)
Each recording becomes a .md file with YAML frontmatter (file_id, title, date, duration, synced_at) followed by AI Summary, Key Highlights, and full Transcript with speaker labels.

## Git
- Identity: Claude Code <claude-code@schoemfeld.de>
- Commit after each working milestone
- Push to origin (https://github.com/wizz-cmd/plaud-sync-cli.git) after each commit
- Start with: remove all TypeScript files, then build Python from scratch
- First commit message: "Rewrite in Python: project structure and CLI skeleton"

## Quality Checklist
Before done:
- All Python source files written
- Runs without errors (python3 -m plaud_sync.cli --help)
- Tests exist and pass (python3 -m pytest test/)
- README.md with usage, install, config docs
- config.example.json included
- LICENSE (MIT, credit Leonard Sellem for original)
- All committed and pushed to GitHub
- Old TypeScript files removed
