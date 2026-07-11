---
name: initialize-atlas-graph
version: 0.1.0
description: >-
  Initialize a repo-keyed research provenance graph (an "Atlas" graph): the persistent
  root that a project's hypotheses, experiments, runs, evidence, and decisions attach to,
  so the research is tracked and reproducible. The graph is keyed off the git repository
  (not the opened folder), so subfolders and fresh clones resolve to the SAME graph;
  creating or linking it is idempotent and dedupe-safe. Use at the start of a research
  project, before you begin recording experiments/runs, or when no graph exists yet for
  this repo. Do NOT use it to generate the hypotheses themselves (use
  `hypothesis-generation`), to detect compute resources (use `get-available-resources`),
  or as a metric logger inside a training loop (use an experiment tracker like MLflow or
  Weights & Biases). This skill only stands up and links the graph root and its schema.
allowed-tools: [Bash, Read, Write]
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Initialize the Atlas Research Graph

## Overview

An **Atlas graph** is a research project's provenance root: a persistent, versioned
ledger that every hypothesis, experiment, training/eval run, piece of evidence, and
decision hangs off. Standing it up once — before the real work starts — is what makes a
research effort auditable and reproducible instead of a pile of disconnected notebooks.

Two properties make the graph trustworthy:

- **Repo-keyed, not path-keyed.** The graph is identified by the *git repository*, so a
  subfolder, a worktree, or a fresh clone at a different absolute path all resolve to the
  **same** graph. Nothing is lost when the checkout moves.
- **Idempotent and dedupe-safe.** Initializing when a graph already exists *links* to the
  existing one and returns its id; it never creates a second, competing root.

This skill only *creates or links* the root and its schema. Populating it with hypotheses,
runs, and evidence is the job of the downstream research skills that reference it.

## When to Use This Skill

- No graph exists yet for this repo (e.g., a canvas/UI reports "no graph for this project",
  or `.atlas/graph.json` is absent).
- The user asks to "initialize", "set up Atlas", or "start tracking" research.
- You are about to begin research work whose hypotheses, experiments, and decisions
  should be recorded and cross-linked.
- A fresh clone or new worktree needs to be *linked* to the project's existing graph.

## When NOT to Use This Skill

- **Generating the hypotheses themselves** — use `hypothesis-generation` (or `hypogenic`
  for LLM-driven hypothesis testing). Their outputs become nodes in *this* graph.
- **Detecting CPU/GPU/memory before a heavy job** — use `get-available-resources`.
- **Logging metrics/params inside a training loop** — that is per-run experiment tracking
  (MLflow, Weights & Biases, DVC). The graph stores the *run node* and its links, not the
  step-by-step loss curve.
- **Literature evidence collection** — use `literature-review` / `citation-management`;
  their citations attach to the graph as `Evidence` nodes but are gathered elsewhere.
- The repo already has a linked graph and you only need to *add* a node — skip
  initialization and append directly (see `references/graph-schema.md`).

## Design Principles

Follow these regardless of the storage backend you choose:

1. **Key off repository identity.** Resolve the git top-level and derive a stable project
   key from the repo (its origin remote if set, else a persisted UUID). Never key off the
   current working directory — it changes.
2. **Check before you create.** Look for an existing manifest first; if present, report its
   `project_id` and stop. This is what makes re-running safe.
3. **Commit the manifest.** The graph root lives *in* the repo (e.g., `.atlas/graph.json`)
   and is committed, so every clone resolves the same graph without a network round-trip.
4. **One canonical root per repo.** If duplicates appear (two clones each created a graph
   before syncing), pick one canonical `project_id` and merge — do not leave two roots.

## Initializing the Graph

The default backend is a single JSON manifest committed at the repo root. This needs only
`git` and `jq` and works offline. (For graph databases and hosted trackers, see
`references/backends-and-troubleshooting.md`.)

**Step 1 — resolve the repo root.** The graph is keyed off the repo, not the CWD:

```bash
root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "not inside a git repo — run 'git init' first, or key by directory path"; }
```

**Step 2 — check for an existing graph (idempotency gate).** If it exists, link and stop:

```bash
if [ -f "$root/.atlas/graph.json" ]; then
  jq -r '"linked existing graph: " + .project_id' "$root/.atlas/graph.json"
  return 0 2>/dev/null || exit 0
fi
```

**Step 3 — derive a stable project key and id.** Prefer the origin remote so re-clones
match; fall back to the repo folder name:

```bash
key="$(git -C "$root" config --get remote.origin.url || basename "$root")"
# macOS: shasum -a 256 ; Linux: sha256sum
project_id="$(printf '%s' "$key" | { shasum -a 256 2>/dev/null || sha256sum; } | cut -c1-16)"
```

**Step 4 — write and stage the manifest:**

```bash
mkdir -p "$root/.atlas"
jq -n --arg id "$project_id" --arg key "$key" --arg ts "$(date -u +%FT%TZ)" \
  '{project_id:$id, repo_key:$key, schema_version:"1", created_at:$ts, nodes:[], edges:[]}' \
  > "$root/.atlas/graph.json"
git -C "$root" add .atlas/graph.json
```

**Step 5 — confirm to the user.** Report the `project_id`, state that the graph is now the
recording root for this repo, and remind them to commit `.atlas/graph.json` so collaborators
and future clones resolve the same graph. From here, downstream skills append nodes.

## The Graph Schema

Nodes model the research narrative and edges model provenance:

| Node        | Represents                                              |
| ----------- | ------------------------------------------------------- |
| `Hypothesis`| A testable claim with a prediction                      |
| `Experiment`| A planned test of one or more hypotheses                |
| `Run`       | A concrete execution (training/eval/simulation) + config|
| `Evidence`  | A result, figure, dataset, or citation                  |
| `Decision`  | A recorded choice (keep/revert/pivot) and its rationale |

Edge examples: `Experiment --tests--> Hypothesis`, `Run --instanceOf--> Experiment`,
`Evidence --supports|refutes--> Hypothesis`, `Decision --basedOn--> Evidence`.

Full field definitions, the append-a-node pattern, and a worked `graph.json` example are in
[`references/graph-schema.md`](references/graph-schema.md).

## Verifying and Failure Modes

Confirm the graph is valid and linked:

```bash
jq -e '.project_id and .schema_version' "$root/.atlas/graph.json" && echo "graph OK"
```

Common failure modes — not-a-git-repo, an already-linked graph, duplicate roots across
clones, an unreachable hosted backend, and a manifest that was gitignored so re-clones
can't find it — with the correct fix for each, are covered in
[`references/backends-and-troubleshooting.md`](references/backends-and-troubleshooting.md).

## References

- [`references/graph-schema.md`](references/graph-schema.md) — node/edge ontology, field
  definitions, the append-a-node pattern, and a worked manifest example.
- [`references/backends-and-troubleshooting.md`](references/backends-and-troubleshooting.md)
  — backend choices (committed JSON ledger, graph DB, hosted trackers), repo-keying and
  dedupe/merge details, verification, and a failure-mode table.
