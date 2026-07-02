---
name: cornelius-propagate-change
version: 0.1.0
description: Propagate staleness from ONE changed note outward through the Brain Dependency Graph and report which downstream notes are now likely stale and need review. Use WHEN a single framework/insight note was substantially edited, the user says their thinking on a topic changed, or new source material contradicts an existing note, and you want to know the blast radius. Do NOT use to score the WHOLE graph at once or generate a health/lifecycle report (use cornelius-coherence-sweep), to discover NEW connections from a note or topic (use cornelius-find-connections), to triage recently-added/orphaned notes (use cornelius-integrate-recent-notes), or to find contradictions between notes (use cornelius-detect-tensions).
argument-hint: <note name>
allowed-tools: [Bash, Read]
user-invocable: true
automation: gated
---

# Propagate Framework/Note Change

When a note is substantially edited, this skill computes which downstream notes may be stale and need review. It seeds a staleness signal at the changed note and pushes it outward across the Brain Dependency Graph's directed edges via the engine's propagation pass.

### How staleness propagates

The signal weakens as it travels, so only genuinely affected notes surface:

- **Edge-type decay** — each dependency edge type (e.g. cites, derives-from, references) carries a different attenuation factor; structural dependencies pass more staleness than loose mentions.
- **Distance decay** — staleness diminishes with each hop from the changed note, so far-removed notes are rarely flagged.
- **Hub dampening** — highly-connected hub notes resist and absorb staleness rather than amplifying it across all their neighbours, preventing graph-wide false alarms.

The result is a per-note staleness score; the CLI surfaces only notes above its review threshold.

## State Dependencies

The CLI reads the graph and writes back updated scores. Locations are relative to the repo root (`git rev-parse --show-toplevel`).

| Source | Location | Read | Write | Purpose |
|--------|----------|------|-------|---------|
| Enrichments | `resources/brain-graph/data/graph_enrichments.json` | ✓ | ✓ | Per-note enrichment store; the propagation pass updates each affected note's staleness score here so later runs and `cornelius-coherence-sweep` see consistent state. |
| LBS Graph | `resources/local-brain-search/data/brain_graph.pkl` | ✓ | | Pickled NetworkX graph (nodes = notes, directed edges = typed dependencies) that defines the topology staleness travels along. Read-only — this skill never mutates structure. |

## Process

### Step 1: Run propagation

```bash
cd "$(git rev-parse --show-toplevel)"/resources/brain-graph
../local-brain-search/venv/bin/python cli.py propagate "<NOTE_NAME>"
```

`<NOTE_NAME>` is the note's title as it appears in the vault (the graph node id), not a file path. Quote it — titles contain spaces.

Optional `--magnitude` (0.0–1.0) scales the seed staleness for a partial edit. Omit it to assume a full rewrite (magnitude 1.0); pass a smaller value for a light touch-up so fewer downstream notes cross the review threshold:
```bash
../local-brain-search/venv/bin/python cli.py propagate "<NOTE_NAME>" --magnitude 0.5
```

### Step 2: Present affected notes

Show the user which notes are flagged for review, sorted by staleness score.

For each affected note, explain:
- Why it's flagged (which upstream change, through what edge type)
- Suggested action: review, update, or mark as OK

### Step 3: Offer to inspect specific notes

If the user wants details on any affected note:
```bash
../local-brain-search/venv/bin/python cli.py inspect "<NOTE_NAME>"
```

## When to Use

- After substantially editing a framework or key insight note
- When the user says they've updated their thinking on a topic
- After ingesting new source material that contradicts existing notes

## When NOT to Use

- **Whole-graph health check** — to recompute staleness/lifecycle/structure across every note and produce a report, use `cornelius-coherence-sweep` instead. This skill is single-seed and targeted.
- **Trivial edits** — a typo fix or formatting change does not warrant propagation; downstream meaning is unchanged.
- **Discovering connections** — to find which notes *relate* to a note (not which are stale), use `cornelius-find-connections`; to triage newly-added or orphaned notes, use `cornelius-integrate-recent-notes`.
- **Note not yet in the graph** — if the note was just created and the LBS graph has not been rebuilt, it has no edges to propagate along; integrate/re-index first.
