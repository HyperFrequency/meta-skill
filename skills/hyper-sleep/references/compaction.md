# Memory log compaction — prompt + format

Detailed reference for the "Memory log compaction" step. The mechanical
rolling is handled by `scripts/compact_memory.py`; this file documents the
summarization prompt and the on-disk format so a human (or `/neuro-surgery`)
can reproduce or audit a consolidation.

## What gets compacted

Source: `04-Agent-Memory/logs.md`, an append-only log. Each entry matches:

```
- [<ISO-8601 timestamp>] action=<verb> scope=<path-or-domain> outcome=<ok|warn|fail> [skill=<slug>] [target=<path>]
```

Entries **older than 7 days** (configurable via `--days`) and **after the
last `> Archived up to <ts>` marker** are eligible. Everything from the last
7 days stays as raw entries.

## Mechanics (no deletion)

`compact_memory.py`:

1. Finds the last `> Archived up to <ts>` marker so it never re-processes
   already-consolidated entries.
2. Groups eligible entries two ways:
   - **by agent/skill** → `04-Agent-Memory/consolidated/agent/<skill>.md`
   - **by workflow** (first path segment of `scope`) →
     `04-Agent-Memory/consolidated/workflow/<workflow-slug>.md`
3. Appends a `## Compacted <date>` block to each consolidated file with the
   raw entries grouped under it.
4. Appends a new `> Archived up to <ts>` marker to `logs.md`. The raw entries
   are **never removed** — the marker only signals that they are superseded by
   the consolidated view for read purposes.

Run `--dry-run` first to preview counts without writing.

## Consolidation summarization prompt

After the script groups raw entries, hyper-sleep summarizes each group into a
short digest at the top of the `## Compacted <date>` block. Use this prompt:

> You are consolidating an agent's activity log. Below are raw log entries
> for a single <agent|workflow> over <date-range>. Produce a 3-6 bullet
> summary capturing: what was accomplished, any recurring failures
> (outcome=fail/warn), and any open follow-ups that a human should know
> about. Do NOT invent outcomes not present in the entries. Preserve exact
> file paths from `target=`/`scope=`. Keep it factual and terse.

## Output format

```markdown
## Compacted 2026-06-29

### Summary (2026-06-15 → 2026-06-21)
- Ingested 4 sources into 02-KB-main/optuna/, all outcome=ok
- 1 recurring warn: qmd not installed on 3 nights → cache warmup skipped
- Open follow-up: stale hub `nautilus/execution` still flagged by neuro-scan

<raw entries, verbatim, preserved below the summary>
- [2026-06-15T02:14:00Z] action=ingest scope=optuna/... outcome=ok skill=crawl-ingest-update target=02-KB-main/optuna/tpe.md
- ...
```

The summary is additive context; the raw entries remain underneath so nothing
is lost. Consolidation is a summarization task, not a deletion.
