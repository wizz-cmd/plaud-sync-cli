# CLAUDE.md Addendum — Urgent Fixes + Meeting Journal

Read this FIRST, then CLAUDE.md. These override/extend the existing spec.

## Context

The Plaud API delivers:
- **Transcript segments:** `[{content, speaker, original_speaker, start_time, end_time}, ...]` as gzip JSON
- **Summary:** `{ai_content: "## Gesprächszusammenfassung\n### Die Stimmung\n..."}` — full markdown with headings
- Field names: `data_type` / `data_link` (not `type` / `url`)
- S3 URLs are `.json.gz` — must gunzip

The hydrator.py already handles gzip + correct field names (commit b0147db). But the normalizer and renderer produce bad output.

## Fix 1: Markdown Rendering — Transcript-focused output

The current `.md` files have Summary, Highlights, Transcript sections — but the summary contains full markdown with `##` headings that break the document hierarchy, and highlights are usually empty.

**New output format for synced .md files:**

```markdown
---
source: plaud
type: recording
file_id: abc123
title: "Meeting Title"
date: 2026-03-23
duration: 25 min
speakers:
  - Christian Schömer
  - Alexander Grimm
---

# Meeting Title

> **Zusammenfassung:** {first 2-3 sentences of summary, plain text, no markdown headings}

## Transcript

**Christian Schömer** (00:00)
So, ich dachte mir, ein Fisher Call ist vielleicht besser...

**Alexander Grimm** (00:12)
Das stimmt, das stimmt ja nicht...

**Christian Schömer** (00:20)
Genau, ja, ich denke...
```

**Rules:**
- `speakers` list in frontmatter (extracted from transcript segments' `speaker` field)
- Summary: flatten to plain text (strip markdown headings), show only first 2-3 sentences as a blockquote
- NO "Highlights" section (Plaud rarely fills it)
- Transcript: each speaker turn as `**Speaker Name** (MM:SS)` with timestamp from `start_time` (convert ms to MM:SS)
- Group consecutive segments by same speaker into one paragraph
- If no transcript available: show "Kein Transcript verfügbar."
- If no summary available: omit the blockquote entirely

**Changes needed:**
- `normalizer.py`: extract speakers list, keep raw segments for timestamp access
- `renderer.py`: implement new format
- `hydrator.py`: already correct (b0147db), don't change

## Fix 2: Meeting Journal as JSONL

Create an append-only JSONL journal following the same pattern as the Posteingang project (PRJ-015).

**New file:** `plaud_sync/journal.py`

**Journal file:** stored alongside the sync state in the sync folder: `{vault}/{sync_folder}/meeting-journal.jsonl`

**Each line is a JSON object:**
```json
{
  "meeting_id": "16b13810c1a4ccdf2c68ffddfd33ab2a",
  "date": "2026-03-23",
  "title": "Abschiedsgespräch: Kündigung, Übergaben und Wechsel",
  "duration_min": 25,
  "speakers": ["Christian Schömer", "Alexander Grimm"],
  "has_transcript": true,
  "has_summary": true,
  "summary_preview": "Nachdenklich, empathisch und pragmatisch...",
  "file": "2026-03-23-abschiedsgespr-ch-k-ndigung-bergaben.md",
  "synced_at": "2026-03-23T16:14:00Z",
  "word_count": 4523
}
```

**Rules:**
- Append-only: new meetings get appended, existing entries (by `meeting_id`) get updated in-place
- `summary_preview`: first 150 chars of summary, plain text
- `speakers`: deduplicated list from transcript segments, named speakers first, "Speaker N" at the end
- `word_count`: word count of the transcript text
- `synced_at`: ISO timestamp of when this entry was written/updated

**Integration in sync.py:**
- After each successful file write (create or update), append/update the journal
- Journal path: `{sync_folder}/meeting-journal.jsonl`

**New CLI subcommand:** `plaud-sync journal`
- Default: pretty-print last 20 entries
- `--period / -p`: filter by date
- `--format json`: raw JSONL output
- `--stats`: show speaker stats, meeting counts by month

## Fix 3: Obsidian Meeting-Journal.md generated from JSONL

**Replace** the current `scripts/update-meeting-journal.py` approach.

Instead: `plaud-sync journal --render-obsidian <path>` generates the Obsidian-compatible Meeting-Journal.md from the JSONL.

This way the JSONL is the source of truth, and the Obsidian file is a rendered view.

The Obsidian file format stays the same as currently (grouped by month, speaker index, wikilinks). But it reads from JSONL instead of parsing all .md files every time.

## Priority Order

1. Fix renderer (transcript-focused .md output) — this is the most visible problem
2. JSONL journal + integration in sync
3. `journal` CLI subcommand
4. Obsidian rendering from JSONL

After implementing, re-run ALL tests (`python3 -m pytest test/ -v`). Then commit each fix separately.

## Do NOT change

- `hydrator.py` — already fixed, don't touch
- `config.py` default filename pattern — already `{date}-{title}`, keep it
- Existing v2 features (period, tui, analyze) — keep them working
