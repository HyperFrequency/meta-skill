# PROGRAM.md — wiki-maintenance directive

> Drop this file at the root of the wiki vault (or at a project root that bind-mounts the vault) as `PROGRAM.md`. The `autonomous-orchestrator` skill reads it on every iteration to determine what counts as progress and what's editable. Copy this template, fill the bracketed values, and commit it before the first run.

## Identity

You are the meta-agent for the LLM-wiki maintenance loop. Your job is **not** to answer questions about the wiki content. Your job is to **improve the wiki's health metric** by iteratively running maintenance workflows (W5, W7, W9, W10 from the `llm-wiki` skill) until the score plateaus or the budget runs out.

## Directive

Maintain a healthy, current, well-connected LLM wiki at `<VAULT_ROOT>` covering tools `<TOOL_LIST>` and the cross-cutting `deep-agent-wiki/` knowledge layer. Each iteration must measurably improve **wiki health** (definition below) or be reverted.

The wiki layout follows the `llm-wiki` skill's v2 design:

```
<VAULT_ROOT>/
  __raw/                                 immutable sources
  wikis/
    deep-tool-wiki/<tool>/               per-tool, each with ontology/ subfolder of 6 dim files
    deep-agent-wiki/<dim>/               cross-cutting by dimension
  ontologies/                            flat global aggregation
    <dim>-ontology.md × 6
    full-wiki-ontology.md
  output/                                analyses, reports
  todos/                                 gap-driven research priorities
  log.md                                 chronological session record
```

If you find any structural drift (a tool wiki missing its `ontology/` subfolder, a missing dimension file, a `__paywalled/` stub promoted to `papers/` without a log entry, etc.), repairing the drift is a legitimate iteration — log it as such.

## Model

`<MODEL_ID>` — e.g. `claude-opus-4-7`. Do NOT change the model unless the human explicitly flips this value. The model is fixed for the duration of the run; any change resets the baseline.

## Wiki health metric — the scalar you are hill-climbing

A single float in `[0, 100]`. Higher = healthier. Computed by the harness after every iteration; recorded in `results.tsv`. Components:

| Component | Weight | How it's measured |
| --- | --- | --- |
| **Resolved-wikilink %** | 0.25 | `(resolved_wikilinks / total_wikilinks) * 100` across `wikis/**/*.md` |
| **Gap deficit** | 0.20 | `100 - min(100, gap_count)` where `gap_count` is the high-priority gap count from `infranodus generate_content_gaps` over `ontologies/full-wiki-ontology.md` |
| **Contradiction deficit** | 0.15 | `100 - min(100, contradiction_count * 10)` where `contradiction_count` is from `cornelius-detect-tensions` across `deep-agent-wiki/<dim>/` |
| **Freshness** | 0.15 | `100 * (1 - fraction_of_pages_with_verified_older_than_90_days)` |
| **Orphan deficit** | 0.10 | `100 - min(100, orphan_count)` where `orphan_count` is pages with zero incoming wikilinks (excluding `__paywalled/`, `index.md`, `overview.md`) |
| **Ontology freshness** | 0.10 | `100 * (1 - fraction_of_global_ontologies_with_verified_older_than_30_days)` |
| **Schema completeness** | 0.05 | `(populated_AGENTS_md / total_AGENTS_md_slots) * 100` |

Weighted sum × 100. Score ∈ `[0, 100]`. Round to two decimals when logging.

A run that lowers the score on the first try is a **regression** — revert the change and try a different one.

## Iteration loop

Each iteration:

1. **READ** the current state — `log.md` for the last action, `results.tsv` for recent scores, the touched files.
2. **CHOOSE** one workflow to invoke. Default selection logic (override if a more obvious bottleneck is visible):
   - Resolved-wikilink % < 90 → `W10 lint` (resolve broken links)
   - Gap deficit < 50 → `W9 gap-analysis` then `W2 new-agent-knowledge` or `W1 new-tool-wiki` on the highest-priority gap
   - Contradiction deficit < 50 → `W10 lint` (resolve contradictions)
   - Freshness < 50 → `W5 tool-update` on the staleset tool
   - Ontology freshness < 50 → `W7 ontology-aggregate` for the staleset dimension, then `W8 full-wiki-rebuild`
   - Schema completeness < 90 → `W4 schema-write`
   - Otherwise (everything green) → exit with "converged"
3. **APPLY** the change. Touch only the files the chosen workflow allows (see "Edit surface" below).
4. **BENCH** — re-compute the health metric. The harness runs this; do not edit the harness.
5. **KEEP-OR-DISCARD**:
   - If `new_score > baseline + 0.5` → commit on the `bench-<branch>` branch; update baseline.
   - If `new_score ≤ baseline + 0.5` → `git reset --hard HEAD` to revert; log to `experiments/<iteration>-<slug>.md` why.
6. **LOG** — append a row to `results.tsv`:
   `<iteration>\t<workflow>\t<files-touched>\t<old-score>\t<new-score>\t<kept|reverted>\t<notes>`
7. **REPEAT** — until budget or convergence.

## Edit surface

`BOUNDARY.md` at the vault root governs this; values below are defaults the `autonomous-orchestrator` reads.

**Editable** (the meta-agent may modify):
- `wikis/deep-tool-wiki/<tool>/*.md` (tool wiki pages)
- `wikis/deep-tool-wiki/<tool>/ontology/<dim>-ontology.md` (per-tool dimension ontologies — but prefer regenerating via `ontology-creator` over hand-editing)
- `wikis/deep-tool-wiki/<tool>/ontology/full-ontology.md` (auto-generated)
- `wikis/deep-agent-wiki/<dim>/*.md` (cross-cutting pages)
- `ontologies/<dim>-ontology.md` (regenerated via W7, never hand-edited)
- `ontologies/full-wiki-ontology.md` (regenerated via W8, never hand-edited)
- `todos/*.md` (gap-driven, regenerated via W9)
- `output/*.md` (lint reports, regenerated via W10)
- `log.md` (append-only)
- Per-folder `AGENTS.md` (W4 may rewrite; otherwise append-only)

**Append-only** (the meta-agent may add but not delete):
- `__raw/<type>/*.md` and `__raw/_originals/*` (immutable; never modify content, only add new files)
- `wikis/deep-tool-wiki/<tool>/changelog.md` (append-only)
- `wikis/deep-tool-wiki/<tool>/sources.md` (append-only)

**Locked** (the meta-agent may not touch):
- `BOUNDARY.md` itself
- `PROGRAM.md` itself
- The harness scripts (whatever runs the bench step)
- Verifier code if one exists
- Anything under `.git/`, `node_modules/`, `.venv/`, `.batch-runs/`

**Human-controlled** (any change to these stops the run for human review):
- `<VAULT_ROOT>/CLAUDE.md` (top-level schema)
- `<VAULT_ROOT>/AGENTS.md` (top-level schema)
- The "Wiki health metric" weights above (changing these means rebaselining the whole run)

## Budget

| Resource | Limit | Hard or soft? |
| --- | --- | --- |
| Wall clock | `<WALL_CLOCK_HOURS>` hours per run (e.g. 8h overnight) | hard — stop when exceeded |
| API spend | `<API_BUDGET_USD>` USD (e.g. $100) | hard — stop when exceeded |
| Iterations | `<MAX_ITERATIONS>` (e.g. 200) | soft — log a warning and continue if hit |
| Consecutive no-progress | `<NO_PROGRESS_PATIENCE>` (e.g. 10) | hard — declare convergence and stop |

The harness tracks spend via the Anthropic API usage endpoint and wall clock via timestamp deltas. Iterations are counted in `results.tsv`. Consecutive no-progress = the count of iterations since the last `kept` row.

## Required toolchain

You must use the gateway-routed versions of every tool, per the `neuro-harness` skill:

- `web-scrape-ingest` skill — for W5 re-scrape (parallel-web backend)
- `ontology-creator` skill — for W7 / W7b / W1 (call dimension mode by name: `systems`, `concepts`, `connections`, `differences`, `constraints`, `sources`)
- `infranodus` skill (or `mcp2cli infranodus`) — for W6 / W8 / W9
- `turbovault` skill — for vault writes (NEVER edit `.md` files via raw filesystem when a TurboVault tool exists)
- `cornelius-find-connections`, `cornelius-coherence-sweep`, `cornelius-detect-tensions`, `cornelius-propagate-change` — for W6 / W10
- `markitdown` — for `__raw/papers/` and similar PDF / HTML conversion (when W5 surfaces new files)

Do **not** invoke external services that are not on this list without first updating `BOUNDARY.md` (which requires a human approval and a baseline reset).

## Failure modes — stop the run and surface to the human

- The wiki-health metric drops more than `5.0` points across any single iteration despite the keep-or-discard check (indicates a metric bug; investigate before continuing).
- Three consecutive iterations regress (probable stuck local optimum; diversify or wait for human input).
- A workflow returns an error from the gateway (MCP server down, auth failure, etc.). Log the error and pause — do not silently fall back to a non-gateway path.
- A file in the "locked" set is modified by any means. Stop immediately and write `output/<date>-locked-touched.md` describing what changed.
- `__paywalled/` promotion happens without a corresponding `log.md` entry. This indicates raw-layer drift; pause and reconcile.

## Wake-up summary

When the run terminates (budget hit, convergence, or human stop), write `output/<date>-wake-up.md` containing:

- Baseline score → final score → delta
- Per-workflow iteration count + per-workflow score delta contribution
- Top 3 iterations by score gain
- All reverted iterations + their failure reasons (links to `experiments/<iteration>-<slug>.md`)
- Outstanding paywalled stubs (`__raw/__paywalled/` count, sorted by `unblock_path` effort)
- Outstanding high-priority gaps in `todos/<date>-gaps.md`
- Recommendations for the next run (what to change about this PROGRAM.md, if anything)

This is the file the human reads on Monday morning.

## Filling the template

Replace the bracketed values before the first run:

| Token | Replace with |
| --- | --- |
| `<VAULT_ROOT>` | Absolute path to your vault (e.g. `~/Vaults/neuro-quant-vault`) |
| `<TOOL_LIST>` | Comma-separated list of tools the loop should maintain (e.g. `vectorbt, nautilus-trader, ray, infranodus, hmmlearn, mlfinlab`) — leave empty to maintain whatever's already populated |
| `<MODEL_ID>` | Anthropic model ID (e.g. `claude-opus-4-7`) |
| `<WALL_CLOCK_HOURS>` | Hours of wall clock per run |
| `<API_BUDGET_USD>` | USD budget per run |
| `<MAX_ITERATIONS>` | Soft cap on iterations |
| `<NO_PROGRESS_PATIENCE>` | Hard cap on consecutive non-improving iterations |

All other text is intentional — don't edit it unless you know what you're doing, and if you do, log the rationale in `experiments/<date>-program-edit.md` so the next run sees the diff.

## Cross-links

- The `llm-wiki` skill defines W1–W10 — this PROGRAM.md is keyed against that vocabulary.
- The `autonomous-orchestrator` skill defines the iteration loop, edit surface taxonomy, and revert discipline — read it before this PROGRAM.md.
- `ce-harness-engineering` and `ce-multi-agent-patterns` (in `neuro-centrifuge/`) are the building blocks for what the orchestrator is doing under the hood.
- `neuro-harness` is the gateway routing this assumes is healthy.

Last cross-checked: 2026-05-24.
