---
name: cornelius-coherence-sweep
version: 0.1.0
description: Run a full coherence sweep across the Brain Dependency Graph - computes note staleness from upstream changes, lifecycle phase transitions, structural health (orphans, overloaded hubs, missing MOCs), and optional productive tensions, then writes a dated markdown report. WHEN to use - the user asks to "sweep", "check coherence", "find stale notes", "audit the brain/knowledge base", or after a batch of edits/imports that may have invalidated downstream notes; also fine on a scheduled cadence. WHEN NOT to use - for editing or refactoring note content (this is read-only analysis), for a single-note lookup or search (use local-brain-search directly), for graph bootstrapping/indexing (run cli.py bootstrap first), or when the Brain Dependency Graph and Local Brain Search index do not exist yet.
argument-hint: "[--days N] [--tensions] [--json]"
allowed-tools: [Bash, Read, Write]
user-invocable: true
automation: gated
---

# Brain Coherence Sweep

Run a full coherence analysis of the knowledge base using the Brain Dependency Graph engine. Identifies stale notes, lifecycle transitions, structural issues, and optionally productive tensions.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| LBS Graph | `resources/local-brain-search/data/brain_graph.pkl` | ✓ | | NetworkX graph |
| Enrichments | `resources/brain-graph/data/graph_enrichments.json` | ✓ | ✓ | Node/edge enrichments |
| Reports | `resources/brain-graph/reports/` | | ✓ | Generated reports |

## Prerequisites

- Brain Dependency Graph must be bootstrapped (`run_brain_graph.sh bootstrap`)
- Local Brain Search index must exist

## Process

### Step 1: Check bootstrap status

```bash
cd "$(git rev-parse --show-toplevel)"/resources/brain-graph
../local-brain-search/venv/bin/python cli.py status
```

If not bootstrapped, run bootstrap first:
```bash
../local-brain-search/venv/bin/python cli.py bootstrap
```

### Step 2: Run coherence sweep

Default (7-day lookback, lifecycle included, no tensions):
```bash
../local-brain-search/venv/bin/python cli.py coherence
```

With options:
```bash
# Include tension detection (slower)
../local-brain-search/venv/bin/python cli.py coherence --tensions

# Custom lookback period
../local-brain-search/venv/bin/python cli.py coherence --days 14

# JSON output
../local-brain-search/venv/bin/python cli.py coherence --json
```

### Step 3: Present results

Read the generated report and present key findings to the user:

1. **Staleness alerts** - Notes that need review due to upstream changes
2. **Lifecycle transitions** - Notes crossing phase boundaries (reflective -> crystallizing -> generative)
3. **Structural health** - Orphans, overloaded hubs, missing MOCs
4. **Tensions** (if enabled) - Productive contradictions for synthesis

Report is saved to: `resources/brain-graph/reports/coherence-report-YYYY-MM-DD.md`

## Output Format

Present a concise summary with:
- Count of stale notes with top 5 most affected
- Notable lifecycle transitions (especially new generative notes)
- Structural issues requiring attention
- Path to full report

## Interpreting Results

- **Staleness** is relative to the `--days N` lookback (default 7). A note is flagged when an upstream dependency it cites changed within the window; a longer window surfaces more (older) drift, a shorter one focuses on recent churn. Staleness is a review signal, not an error — do not auto-edit flagged notes.
- **Lifecycle transitions** move a note along `reflective -> crystallizing -> generative`. New `generative` notes are the highest-value signal (ideas ready to be built on); a note slipping backward usually means upstream context shifted.
- **Structural health**: `orphans` (no inbound/outbound links) are candidates for linking or archiving; `overloaded hubs` (very high degree) are split/MOC candidates; `missing MOCs` flag clusters with no map-of-content anchor.
- **Tensions** (only with `--tensions`) are productive contradictions between notes, surfaced for synthesis. Detection is slower and graph-size dependent — skip it for quick sweeps.

## Edge Cases & Failure Modes

- **Not bootstrapped / missing index**: `cli.py status` reports an unbuilt graph. Run `cli.py bootstrap` first; do not run `coherence` against a stale or partial graph.
- **Empty / tiny graph**: a freshly bootstrapped graph yields near-empty reports — confirm the Local Brain Search index actually covers the vault before reading too much into low counts.
- **No upstream changes in window**: zero stale notes is a valid result, not a failure. Report it as a clean sweep rather than widening `--days` automatically.
- **`--json` mode**: emits machine-readable output instead of the markdown report path — use it for piping into other tooling, not for the human summary above.
- Report writes are idempotent per day: re-running overwrites `coherence-report-YYYY-MM-DD.md` for the current date rather than appending.
