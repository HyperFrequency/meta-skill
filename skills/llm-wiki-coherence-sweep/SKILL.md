---
name: llm-wiki-coherence-sweep
version: 0.2.0
description: Run a whole-vault coherence sweep over the knowledge-base dependency graph - in ONE read-only pass it computes note staleness from upstream changes, lifecycle transitions (reflective -> crystallizing -> generative), structural health (orphans, overloaded hubs, missing MOCs), and optional productive tensions, then writes a dated markdown report. WHEN - the user asks to "sweep", "check coherence", "audit the vault/knowledge base", "find stale notes", or after a batch of edits/imports that may have invalidated downstream notes; also fine on a schedule. WHEN NOT - blast radius of ONE changed note (use llm-wiki-propagate-change), structure/clusters/hubs only (use llm-wiki-analyze-kb), recently-added notes only (use llm-wiki-integrate-recent-notes), contradictions only (use llm-wiki-detect-tensions), editing note content or single-note lookup/search (query via turbovault; this never writes notes), or before the graph and index exist (bootstrap first).
argument-hint: "[--days N] [--tensions] [--json]"
allowed-tools: [Bash, Read, Write]
user-invocable: true
automation: gated
---

# Coherence Sweep

Run a full coherence analysis over the user's neuro-quant Obsidian vault (`~/Vaults/neuro-quant-vault`) using the knowledge-base dependency-graph engine. In a single pass it surfaces stale notes, lifecycle transitions, structural issues, and (optionally) productive tensions, then writes a dated report.

This is the **fleet-wide** analysis in the `llm-wiki-*` family: it scores the *entire* graph at once. For single-note or single-concern passes, use the sibling skill named in the boundaries below.

## State dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Graph index | `resources/local-brain-search/data/brain_graph.pkl` | ✓ | | NetworkX dependency graph over the vault |
| Enrichments | `resources/brain-graph/data/graph_enrichments.json` | ✓ | ✓ | Node/edge enrichments (staleness, lifecycle) |
| Reports | `resources/brain-graph/reports/` | | ✓ | Generated coherence reports |

## Prerequisites

- The dependency graph must be bootstrapped (`run_brain_graph.sh bootstrap`).
- The vault search index must exist. If either is missing, bootstrap first — do not run `coherence` against a stale or partial graph.

## Process

### Step 1 — check bootstrap status

```bash
cd "$(git rev-parse --show-toplevel)"/resources/brain-graph
../local-brain-search/venv/bin/python cli.py status
```

If not bootstrapped:
```bash
../local-brain-search/venv/bin/python cli.py bootstrap
```

### Step 2 — run the sweep

```bash
# Default: 7-day lookback, lifecycle included, no tensions
../local-brain-search/venv/bin/python cli.py coherence

# Include tension detection (slower, graph-size dependent)
../local-brain-search/venv/bin/python cli.py coherence --tensions

# Custom lookback window
../local-brain-search/venv/bin/python cli.py coherence --days 14

# Machine-readable output (for piping, not the human summary)
../local-brain-search/venv/bin/python cli.py coherence --json
```

### Step 3 — present results

Read the generated report (`resources/brain-graph/reports/coherence-report-YYYY-MM-DD.md`) and summarize:

1. **Staleness alerts** — notes needing review due to upstream changes.
2. **Lifecycle transitions** — notes crossing phase boundaries (reflective → crystallizing → generative).
3. **Structural health** — orphans, overloaded hubs, missing MOCs.
4. **Tensions** (only if `--tensions`) — productive contradictions surfaced for synthesis.

## Output format

A concise summary with:
- Count of stale notes plus the top 5 most affected.
- Notable lifecycle transitions (especially new `generative` notes).
- Structural issues requiring attention.
- Path to the full report.

## Interpreting results

- **Staleness** is relative to the `--days N` lookback (default 7). A note is flagged when an upstream dependency it cites changed within the window; a longer window surfaces more (older) drift, a shorter one focuses on recent churn. Staleness is a review signal, not an error — never auto-edit flagged notes.
- **Lifecycle transitions** move a note along `reflective → crystallizing → generative`. New `generative` notes are the highest-value signal (ideas ready to be built on); a note slipping backward usually means upstream context shifted.
- **Structural health**: `orphans` (no inbound/outbound links) are candidates for linking or archiving; `overloaded hubs` (very high degree) are split/MOC candidates; `missing MOCs` flag clusters with no map-of-content anchor.
- **Tensions** (only with `--tensions`) are productive contradictions between notes, surfaced for synthesis. Detection is slower and graph-size dependent — skip it for quick sweeps.

## Edge cases & failure modes

- **Not bootstrapped / missing index**: `cli.py status` reports an unbuilt graph. Bootstrap first; do not run `coherence` against a stale or partial graph.
- **Empty / tiny graph**: a freshly bootstrapped graph yields near-empty reports — confirm the index actually covers the vault before reading too much into low counts.
- **No upstream changes in window**: zero stale notes is a valid result, not a failure. Report it as a clean sweep rather than widening `--days` automatically.
- **`--json` mode**: emits machine-readable output instead of the markdown report path — use it for piping into other tooling, not for the human summary.
- Report writes are idempotent per day: re-running overwrites `coherence-report-YYYY-MM-DD.md` for the current date rather than appending.

## Boundaries — sibling `llm-wiki-*` skills

- Blast radius of **one** changed note → `llm-wiki-propagate-change`.
- Structure / clusters / hubs / bridges profile only → `llm-wiki-analyze-kb`.
- Triage of recently added/modified notes only → `llm-wiki-integrate-recent-notes`.
- Contradictions between notes only → `llm-wiki-detect-tensions`.
- Discovering new connections around a note/topic → `llm-wiki-find-connections`.
- Editing/refactoring note content, or single-note lookup/search → not this skill (query the vault via `turbovault`; this skill is read-only).
